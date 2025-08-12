"""
Analysis Worker Module - Worker Thread Pool for Task Processing

This module implements the worker thread pool that processes analysis tasks from
the monitoring service queue. Workers consume tasks, execute heavy AI analysis,
and report results to the backend system.

Key Features:
- Worker thread pool consuming tasks from Phase 1 monitoring queue
- Task processing through AnalysisService with complete AI pipeline
- Backend communication via enhanced event_reporter for violation reporting
- Error handling, retry logic, and comprehensive performance tracking
- Worker health monitoring and dynamic scaling capabilities

Architecture:
- AnalysisWorker: Individual worker threads processing tasks
- WorkerPool: Worker pool management and coordination
- TaskProcessor: Task lifecycle management and execution
- EventReporter: Backend communication and violation reporting
"""

import logging
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import psutil
import traceback

# Import core services and models
from core.analysis import AnalysisService
from models import (
    AnalysisTask, AnalysisResult, ViolationReport, TaskStatus, 
    TaskPriority, PerformanceMetrics, SystemHealth
)
from event_reporter import EventReporter
from utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)


@dataclass
class WorkerStats:
    """Statistics for individual worker performance"""
    worker_id: str
    tasks_processed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    total_processing_time: float = 0.0
    avg_processing_time: float = 0.0
    last_task_time: Optional[datetime] = None
    is_active: bool = False
    current_task_id: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class PoolStats:
    """Statistics for the entire worker pool"""
    active_workers: int = 0
    total_workers: int = 0
    queue_size: int = 0
    queue_max_size: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    avg_processing_time: float = 0.0
    throughput_per_minute: float = 0.0
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class TaskProcessor:
    """Handles task lifecycle management and execution"""
    
    def __init__(self, worker_id: str, analysis_service: AnalysisService, 
                 event_reporter: EventReporter):
        self.worker_id = worker_id
        self.analysis_service = analysis_service
        self.event_reporter = event_reporter
        
        # Processing configuration
        self.max_retries = 3
        self.retry_delay = 5.0
        
    def process_task(self, task: AnalysisTask) -> bool:
        """Process a single analysis task"""
        try:
            # Mark task as started
            task.start_processing(self.worker_id)
            
            logger.info(f"Worker {self.worker_id} processing task {task.task_id}")
            
            # Execute analysis through AnalysisService
            analysis_result = self.analysis_service.analyze_violation(task)
            
            # Check if this is actually a violation that should be reported
            if self._should_report_violation(analysis_result):
                # Create violation report
                cctv_id = self._get_cctv_id_from_stream(analysis_result.parking_event.stream_id)
                violation_report = self.analysis_service.create_violation_report(
                    analysis_result, cctv_id
                )
                
                # Send to backend
                backend_response = self.event_reporter.send_violation_report(violation_report)
                
                if backend_response.success:
                    task.complete_processing()
                    logger.info(f"Task {task.task_id} completed successfully, "
                              f"violation reported to backend")
                    return True
                else:
                    error_msg = f"Backend error: {backend_response.message}"
                    return self._handle_task_failure(task, error_msg)
            else:
                # Task completed but no violation to report
                task.complete_processing()
                logger.info(f"Task {task.task_id} completed, no violation detected")
                return True
                
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"Worker {self.worker_id} task {task.task_id} failed: {error_msg}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return self._handle_task_failure(task, error_msg)
    
    def _should_report_violation(self, analysis_result: AnalysisResult) -> bool:
        """Determine if analysis result should be reported as violation"""
        # Report if AI model detected illegal parking with reasonable confidence
        return (
            analysis_result.is_illegal_by_model and 
            analysis_result.model_confidence > 0.6
        )
    
    def _get_cctv_id_from_stream(self, stream_id: str) -> int:
        """Get CCTV ID from stream ID (implement mapping logic)"""
        # For now, extract numeric part from stream ID
        try:
            # Extract number from stream_id like "cctv_001" -> 1
            if stream_id.startswith("cctv_"):
                return int(stream_id.split("_")[1])
            else:
                return hash(stream_id) % 1000  # Fallback hash-based ID
        except:
            return 0  # Default fallback
    
    def _handle_task_failure(self, task: AnalysisTask, error_message: str) -> bool:
        """Handle task failure with retry logic"""
        if task.retry_processing():
            logger.warning(f"Retrying task {task.task_id} (attempt {task.retry_count})")
            # Task will be re-queued by worker
            return False  # Indicates retry needed
        else:
            task.fail_processing(error_message)
            logger.error(f"Task {task.task_id} failed permanently: {error_message}")
            return True  # Task completed (failed)


class AnalysisWorker(threading.Thread):
    """Worker thread for processing analysis tasks from queue"""
    
    def __init__(self, worker_id: str, task_queue: queue.Queue,
                 analysis_service: AnalysisService, event_reporter: EventReporter,
                 config: Dict[str, Any]):
        super().__init__(name=f"AnalysisWorker-{worker_id}", daemon=True)
        
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.analysis_service = analysis_service
        self.event_reporter = event_reporter
        self.config = config
        
        # Task processor
        self.task_processor = TaskProcessor(worker_id, analysis_service, event_reporter)
        
        # Worker state
        self.is_running = False
        self.is_paused = False
        self.current_task: Optional[AnalysisTask] = None
        
        # Performance tracking
        self.stats = WorkerStats(worker_id=worker_id)
        self.start_time: Optional[float] = None
        
        # Configuration
        self.processing_config = config.get('processing', {})
        self.heartbeat_interval = self.processing_config.get('heartbeat_interval', 30.0)
        self.queue_timeout = self.processing_config.get('queue_timeout', 1.0)
        
        # Health monitoring
        self.last_heartbeat = time.time()
        self.health_callbacks: List[Callable[[str, SystemHealth], None]] = []
        
        logger.info(f"AnalysisWorker {worker_id} created")
    
    def start_worker(self) -> bool:
        """Start the worker thread"""
        if self.is_running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return True
        
        try:
            self.is_running = True
            self.is_paused = False
            self.start_time = time.time()
            self.stats.is_active = True
            
            self.start()  # Start thread
            logger.info(f"Worker {self.worker_id} started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            self.is_running = False
            return False
    
    def run(self):
        """Main worker loop - consume and process tasks"""
        logger.info(f"Worker {self.worker_id} main loop started")
        
        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                try:
                    # Get task from queue with timeout
                    task = self.task_queue.get(timeout=self.queue_timeout)
                    self.current_task = task
                    
                    # Process task
                    task_start_time = time.time()
                    success = self.task_processor.process_task(task)
                    task_duration = time.time() - task_start_time
                    
                    # Update statistics
                    self._update_task_stats(task, task_duration, success)
                    
                    # Handle retry if needed
                    if not success and task.status == TaskStatus.RETRYING:
                        self.task_queue.put(task)  # Re-queue for retry
                        self.stats.tasks_retried += 1
                        time.sleep(self.task_processor.retry_delay)
                    
                    self.current_task = None
                    
                except queue.Empty:
                    # No tasks available, continue loop
                    continue
                except Exception as e:
                    logger.error(f"Worker {self.worker_id} unexpected error: {e}")
                    self.stats.error_count += 1
                    self.stats.last_error = str(e)
                finally:
                    if 'task' in locals():
                        self.task_queue.task_done()
                
                # Periodic health check
                self._check_health()
                
        except Exception as e:
            logger.error(f"Worker {self.worker_id} main loop error: {e}")
        finally:
            self.stats.is_active = False
            logger.info(f"Worker {self.worker_id} main loop ended")
    
    def _update_task_stats(self, task: AnalysisTask, duration: float, success: bool):
        """Update worker statistics after task completion"""
        self.stats.tasks_processed += 1
        self.stats.total_processing_time += duration
        self.stats.last_task_time = datetime.now()
        
        if not success:
            self.stats.tasks_failed += 1
        
        # Update average processing time
        if self.stats.tasks_processed > 0:
            self.stats.avg_processing_time = (
                self.stats.total_processing_time / self.stats.tasks_processed
            )
    
    def _check_health(self):
        """Perform periodic health check"""
        current_time = time.time()
        
        if current_time - self.last_heartbeat >= self.heartbeat_interval:
            # Create health status
            health_status = self._create_health_status()
            
            # Trigger health callbacks
            for callback in self.health_callbacks:
                try:
                    callback(self.worker_id, health_status)
                except Exception as e:
                    logger.error(f"Error in health callback: {e}")
            
            self.last_heartbeat = current_time
    
    def _create_health_status(self) -> SystemHealth:
        """Create current health status for this worker"""
        # Determine health status
        if not self.is_running:
            status = "critical"
            message = "Worker not running"
        elif self.stats.error_count > 10:
            status = "warning"
            message = f"High error count: {self.stats.error_count}"
        elif self.stats.tasks_processed == 0:
            status = "warning"
            message = "No tasks processed yet"
        else:
            status = "healthy"
            message = f"Processing normally, {self.stats.tasks_processed} tasks completed"
        
        # Collect metrics
        metrics = {
            "tasks_processed": self.stats.tasks_processed,
            "tasks_failed": self.stats.tasks_failed,
            "avg_processing_time": self.stats.avg_processing_time,
            "error_count": self.stats.error_count,
            "uptime_seconds": time.time() - self.start_time if self.start_time else 0,
            "current_task": self.current_task.task_id if self.current_task else None
        }
        
        return SystemHealth(
            component=f"worker-{self.worker_id}",
            status=status,
            message=message,
            metrics=metrics
        )
    
    def pause_worker(self):
        """Pause worker processing"""
        self.is_paused = True
        logger.info(f"Worker {self.worker_id} paused")
    
    def resume_worker(self):
        """Resume worker processing"""
        self.is_paused = False
        logger.info(f"Worker {self.worker_id} resumed")
    
    def stop_worker(self):
        """Stop worker processing"""
        self.is_running = False
        logger.info(f"Worker {self.worker_id} stopping")
    
    def add_health_callback(self, callback: Callable[[str, SystemHealth], None]):
        """Add callback for health status updates"""
        self.health_callbacks.append(callback)
    
    def get_stats(self) -> WorkerStats:
        """Get current worker statistics"""
        return self.stats


class WorkerPool:
    """Manages pool of analysis worker threads"""
    
    def __init__(self, pool_size: int, task_queue: queue.Queue, 
                 analysis_service: AnalysisService, config: Dict[str, Any]):
        self.pool_size = pool_size
        self.task_queue = task_queue
        self.analysis_service = analysis_service
        self.config = config
        
        # Event reporter for backend communication
        self.event_reporter = EventReporter(config.get('backend', {}))
        
        # Worker management
        self.workers: List[AnalysisWorker] = []
        self.is_running = False
        
        # Performance tracking
        self.start_time: Optional[float] = None
        self.pool_stats = PoolStats()
        
        # Health monitoring
        self.health_check_interval = 60.0  # seconds
        self.last_health_check = 0.0
        
        logger.info(f"WorkerPool created with {pool_size} workers")
    
    def start_workers(self) -> bool:
        """Start all worker threads"""
        if self.is_running:
            logger.warning("Worker pool is already running")
            return True
        
        try:
            logger.info(f"Starting {self.pool_size} analysis workers...")
            
            # Create and start workers
            success_count = 0
            for i in range(self.pool_size):
                worker_id = f"worker-{i:02d}"
                
                worker = AnalysisWorker(
                    worker_id=worker_id,
                    task_queue=self.task_queue,
                    analysis_service=self.analysis_service,
                    event_reporter=self.event_reporter,
                    config=self.config
                )
                
                # Add health monitoring callback
                worker.add_health_callback(self._worker_health_callback)
                
                if worker.start_worker():
                    self.workers.append(worker)
                    success_count += 1
                else:
                    logger.error(f"Failed to start worker {worker_id}")
            
            if success_count > 0:
                self.is_running = True
                self.start_time = time.time()
                logger.info(f"Started {success_count}/{self.pool_size} workers successfully")
                return True
            else:
                logger.error("Failed to start any workers")
                return False
                
        except Exception as e:
            logger.error(f"Error starting worker pool: {e}")
            return False
    
    def stop_workers(self):
        """Stop all worker threads"""
        if not self.is_running:
            return
        
        logger.info("Stopping worker pool...")
        
        # Stop all workers
        for worker in self.workers:
            worker.stop_worker()
        
        # Wait for workers to finish
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=10.0)
                if worker.is_alive():
                    logger.warning(f"Worker {worker.worker_id} did not stop gracefully")
        
        self.workers.clear()
        self.is_running = False
        
        logger.info("Worker pool stopped")
    
    def pause_workers(self):
        """Pause all workers"""
        for worker in self.workers:
            worker.pause_worker()
        logger.info("All workers paused")
    
    def resume_workers(self):
        """Resume all workers"""
        for worker in self.workers:
            worker.resume_worker()
        logger.info("All workers resumed")
    
    def _worker_health_callback(self, worker_id: str, health: SystemHealth):
        """Handle health status updates from workers"""
        if not health.is_healthy():
            logger.warning(f"Worker {worker_id} health issue: {health.message}")
    
    def get_pool_stats(self) -> PoolStats:
        """Get comprehensive worker pool statistics"""
        current_time = time.time()
        
        # Update basic stats
        self.pool_stats.active_workers = len([w for w in self.workers if w.stats.is_active])
        self.pool_stats.total_workers = len(self.workers)
        self.pool_stats.queue_size = self.task_queue.qsize()
        self.pool_stats.queue_max_size = self.task_queue.maxsize
        
        # Aggregate worker statistics
        total_processed = sum(w.stats.tasks_processed for w in self.workers)
        total_failed = sum(w.stats.tasks_failed for w in self.workers)
        total_retried = sum(w.stats.tasks_retried for w in self.workers)
        
        self.pool_stats.total_processed = total_processed
        self.pool_stats.total_failed = total_failed
        self.pool_stats.total_retried = total_retried
        
        # Calculate average processing time
        processing_times = [w.stats.avg_processing_time for w in self.workers 
                          if w.stats.avg_processing_time > 0]
        if processing_times:
            self.pool_stats.avg_processing_time = sum(processing_times) / len(processing_times)
        
        # Calculate throughput
        if self.start_time:
            uptime_minutes = (current_time - self.start_time) / 60.0
            self.pool_stats.uptime_seconds = uptime_minutes * 60
            if uptime_minutes > 0:
                self.pool_stats.throughput_per_minute = total_processed / uptime_minutes
        
        # System resource usage
        try:
            process = psutil.Process()
            self.pool_stats.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.pool_stats.cpu_usage_percent = process.cpu_percent()
        except:
            pass
        
        return self.pool_stats
    
    def get_worker_stats(self) -> List[WorkerStats]:
        """Get statistics for all individual workers"""
        return [worker.get_stats() for worker in self.workers]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for the entire pool"""
        current_time = time.time()
        
        # Check if health check is needed
        if current_time - self.last_health_check >= self.health_check_interval:
            self.last_health_check = current_time
        
        # Collect health information
        healthy_workers = 0
        warning_workers = 0
        critical_workers = 0
        
        for worker in self.workers:
            health = worker._create_health_status()
            if health.status == "healthy":
                healthy_workers += 1
            elif health.status == "warning":
                warning_workers += 1
            elif health.status == "critical":
                critical_workers += 1
        
        # Determine overall pool health
        if critical_workers > 0:
            pool_status = "critical"
            pool_message = f"{critical_workers} workers critical"
        elif warning_workers > len(self.workers) // 2:
            pool_status = "warning"
            pool_message = f"{warning_workers} workers have warnings"
        elif healthy_workers == len(self.workers):
            pool_status = "healthy"
            pool_message = "All workers healthy"
        else:
            pool_status = "warning"
            pool_message = f"{healthy_workers}/{len(self.workers)} workers healthy"
        
        return {
            "pool_status": pool_status,
            "pool_message": pool_message,
            "healthy_workers": healthy_workers,
            "warning_workers": warning_workers,
            "critical_workers": critical_workers,
            "total_workers": len(self.workers),
            "is_running": self.is_running
        }