"""
Standalone AI Processor for Illegal Parking Detection
Main orchestration module for two-phase processing architecture

This module serves as the main entry point for the standalone AI processor that
replaces the previous FastAPI web server. It implements a two-phase architecture:
- Phase 1: Continuous lightweight monitoring across multiple CCTV streams
- Phase 2: Event-driven heavy AI analysis for detailed violation processing

Key Features:
- Standalone processor (no web server dependencies)
- Two-phase architecture with task queue communication
- Multi-YAML configuration system integration
- Worker thread pool for scalable processing
- Graceful startup/shutdown with signal handling
- Comprehensive system health monitoring

Architecture:
- IllegalParkingProcessor: Main application coordinator
- Phase 1: MonitoringService for continuous stream watching
- Phase 2: AnalysisService + WorkerPool for heavy processing
- Task queue connecting phases with violation candidates
"""

import asyncio
import signal
import sys
import time
import threading
from pathlib import Path
from queue import Queue
from typing import Dict, Any, Optional
import psutil

# Add ai_server to path for imports
sys.path.append(str(Path(__file__).parent))

# Import core components
from utils.config_loader import load_config
from utils.logger import setup_logging, get_logger
from core.monitoring import MonitoringService
from core.analysis import AnalysisService
from workers.analysis_worker import WorkerPool
from models import AnalysisTask, SystemHealth

# Import existing AI components for initialization
from cctv_manager import initialize_cctv_manager
from multi_vehicle_tracker import initialize_vehicle_tracker
from parking_monitor import initialize_parking_monitor
from license_plate_detector import initialize_license_plate_detector
from ocr_reader import initialize_ocr_reader
from illegal_classifier import initialize_violation_classifier

# Configure logging
logger = get_logger("main")


class IllegalParkingProcessor:
    """Main processor coordinating both phases of the illegal parking detection system"""
    
    def __init__(self):
        # Configuration
        self.config: Optional[Dict[str, Any]] = None
        
        # Core services
        self.monitoring_service: Optional[MonitoringService] = None
        self.analysis_service: Optional[AnalysisService] = None
        self.worker_pool: Optional[WorkerPool] = None
        
        # Task queue (Phase 1 → Phase 2 communication)
        self.task_queue: Optional[Queue] = None
        
        # System state
        self.is_running = False
        self.start_time: Optional[float] = None
        
        # Health monitoring
        self.health_monitor_thread: Optional[threading.Thread] = None
        self.health_check_interval = 60.0  # seconds
        
        # Performance tracking
        self.system_stats = {
            'uptime': 0.0,
            'total_violations_processed': 0,
            'memory_usage_mb': 0.0,
            'cpu_usage_percent': 0.0
        }
        
        logger.info("IllegalParkingProcessor created")
    
    async def initialize(self) -> bool:
        """Initialize all components and AI models"""
        try:
            logger.info("Initializing Illegal Parking Detection Processor...")
            
            # 1. Load multi-YAML configuration
            logger.info("Loading configuration...")
            self.config = load_config()
            
            # 2. Setup logging system
            setup_logging(self.config.get('logging', {}))
            logger.info("Logging system configured")
            
            # 3. Initialize AI components
            logger.info("Initializing AI components...")
            ai_init_success = await self._initialize_ai_components()
            if not ai_init_success:
                logger.error("Failed to initialize AI components")
                return False
            
            # 4. Initialize task queue
            queue_size = self.config.get('processing', {}).get('queue_max_size', 100)
            self.task_queue = Queue(maxsize=queue_size)
            logger.info(f"Task queue initialized with max size {queue_size}")
            
            # 5. Initialize core services
            logger.info("Initializing core services...")
            if not await self._initialize_core_services():
                logger.error("Failed to initialize core services")
                return False
            
            # 6. Initialize worker pool
            logger.info("Initializing worker pool...")
            if not self._initialize_worker_pool():
                logger.error("Failed to initialize worker pool")
                return False
            
            logger.info("Processor initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def _initialize_ai_components(self) -> bool:
        """Initialize all AI components with configuration"""
        try:
            # Initialize AI components with configuration
            components_success = [
                ("CCTV Manager", initialize_cctv_manager(self.config)),
                ("Vehicle Tracker", initialize_vehicle_tracker(self.config)),
                ("Parking Monitor", initialize_parking_monitor(self.config)),
                ("License Plate Detector", initialize_license_plate_detector(self.config)),
                ("OCR Reader", initialize_ocr_reader(self.config)),
                ("Violation Classifier", initialize_violation_classifier(self.config))
            ]
            
            all_success = True
            for name, success in components_success:
                status = "✓ Initialized" if success else "✗ Failed"
                logger.info(f"AI Component {name}: {status}")
                if not success:
                    all_success = False
            
            return all_success
            
        except Exception as e:
            logger.error(f"Error initializing AI components: {e}")
            return False
    
    async def _initialize_core_services(self) -> bool:
        """Initialize monitoring and analysis services"""
        try:
            # Initialize monitoring service (Phase 1)
            self.monitoring_service = MonitoringService(self.config)
            if not self.monitoring_service.initialize_components(self.task_queue):
                logger.error("Failed to initialize monitoring service components")
                return False
            
            # Initialize analysis service (Phase 2)
            self.analysis_service = AnalysisService(self.config)
            if not self.analysis_service.initialize_models():
                logger.error("Failed to initialize analysis service models")
                return False
            
            logger.info("Core services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing core services: {e}")
            return False
    
    def _initialize_worker_pool(self) -> bool:
        """Initialize worker thread pool"""
        try:
            pool_size = self.config.get('processing', {}).get('worker_pool_size', 3)
            
            self.worker_pool = WorkerPool(
                pool_size=pool_size,
                task_queue=self.task_queue,
                analysis_service=self.analysis_service,
                config=self.config
            )
            
            logger.info(f"Worker pool initialized with {pool_size} workers")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing worker pool: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the two-phase processing system"""
        if self.is_running:
            logger.warning("Processor is already running")
            return True
        
        try:
            # Initialize if not already done
            if not self.config:
                if not await self.initialize():
                    return False
            
            logger.info("Starting Illegal Parking Processor...")
            
            # 1. Start worker pool (Phase 2)
            logger.info("Starting worker pool...")
            if not self.worker_pool.start_workers():
                logger.error("Failed to start worker pool")
                return False
            
            # 2. Start monitoring service (Phase 1)
            logger.info("Starting monitoring service...")
            if not await self.monitoring_service.start_monitoring():
                logger.error("Failed to start monitoring service")
                await self.shutdown()
                return False
            
            # 3. Start health monitoring
            self._start_health_monitoring()
            
            # 4. Mark system as running
            self.is_running = True
            self.start_time = time.time()
            
            logger.info("Illegal Parking Processor started successfully")
            logger.info(f"System Status:")
            logger.info(f"  - Monitoring: {len(self.monitoring_service.get_active_streams())} streams")
            logger.info(f"  - Workers: {self.worker_pool.pool_size} analysis workers")
            logger.info(f"  - Queue: {self.task_queue.maxsize} max tasks")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting processor: {e}")
            await self.shutdown()
            return False
    
    def _start_health_monitoring(self):
        """Start background health monitoring"""
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="HealthMonitor",
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info("Health monitoring started")
    
    def _health_monitor_loop(self):
        """Background health monitoring loop"""
        logger.info("Health monitor loop started")
        
        while self.is_running:
            try:
                # Update system statistics
                self._update_system_stats()
                
                # Log system status periodically
                if time.time() % 300 < self.health_check_interval:  # Every 5 minutes
                    self._log_system_status()
                
                # Sleep until next check
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                time.sleep(self.health_check_interval)
        
        logger.info("Health monitor loop ended")
    
    def _update_system_stats(self):
        """Update system performance statistics"""
        try:
            # Update uptime
            if self.start_time:
                self.system_stats['uptime'] = time.time() - self.start_time
            
            # Update resource usage
            process = psutil.Process()
            self.system_stats['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
            self.system_stats['cpu_usage_percent'] = process.cpu_percent()
            
            # Update violation count
            if self.monitoring_service:
                monitoring_stats = self.monitoring_service.get_monitoring_stats()
                self.system_stats['total_violations_processed'] = monitoring_stats.get(
                    'total_violations_detected', 0
                )
            
        except Exception as e:
            logger.error(f"Error updating system stats: {e}")
    
    def _log_system_status(self):
        """Log comprehensive system status"""
        try:
            logger.info("=== System Status Report ===")
            
            # Basic system info
            uptime_hours = self.system_stats['uptime'] / 3600.0
            logger.info(f"Uptime: {uptime_hours:.1f} hours")
            logger.info(f"Memory: {self.system_stats['memory_usage_mb']:.1f} MB")
            logger.info(f"CPU: {self.system_stats['cpu_usage_percent']:.1f}%")
            
            # Monitoring service status
            if self.monitoring_service:
                monitoring_stats = self.monitoring_service.get_monitoring_stats()
                logger.info(f"Monitoring: {monitoring_stats['active_streams']} streams, "
                          f"{monitoring_stats['total_violations_detected']} violations detected")
                logger.info(f"Average FPS: {monitoring_stats.get('average_fps', 0):.1f}")
            
            # Worker pool status
            if self.worker_pool:
                pool_stats = self.worker_pool.get_pool_stats()
                logger.info(f"Workers: {pool_stats.active_workers}/{pool_stats.total_workers} active")
                logger.info(f"Queue: {pool_stats.queue_size}/{pool_stats.queue_max_size} tasks")
                logger.info(f"Processed: {pool_stats.total_processed} tasks "
                          f"({pool_stats.throughput_per_minute:.1f}/min)")
                
                if pool_stats.total_processed > 0:
                    success_rate = 1.0 - (pool_stats.total_failed / pool_stats.total_processed)
                    logger.info(f"Success Rate: {success_rate:.1%}")
            
            # Analysis service status
            if self.analysis_service:
                analysis_stats = self.analysis_service.get_analysis_stats()
                logger.info(f"Analysis: {analysis_stats['total_processed']} processed, "
                          f"{analysis_stats['violations_confirmed']} violations confirmed")
                logger.info(f"OCR Success Rate: {analysis_stats['ocr_success_rate']:.1%}")
            
            logger.info("=== End Status Report ===")
            
        except Exception as e:
            logger.error(f"Error logging system status: {e}")
    
    async def run_main_loop(self):
        """Main processing loop - keep system running"""
        logger.info("Entering main processing loop...")
        
        try:
            while self.is_running:
                # The actual processing happens in background threads:
                # - MonitoringService handles Phase 1 (stream monitoring)
                # - WorkerPool handles Phase 2 (analysis processing)
                # This loop just keeps the main thread alive and handles shutdown
                
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            logger.info("Main processing loop ended")
    
    async def shutdown(self):
        """Graceful shutdown of the entire system"""
        if not self.is_running:
            return
        
        logger.info("Shutting down Illegal Parking Processor...")
        
        self.is_running = False
        
        try:
            # 1. Stop monitoring service (Phase 1)
            if self.monitoring_service:
                logger.info("Stopping monitoring service...")
                await self.monitoring_service.stop_monitoring()
            
            # 2. Wait for task queue to empty
            if self.task_queue:
                logger.info("Waiting for task queue to empty...")
                try:
                    # Wait for all tasks to complete (with timeout)
                    self.task_queue.join()
                except:
                    pass  # Queue might be empty or already shut down
            
            # 3. Stop worker pool (Phase 2)
            if self.worker_pool:
                logger.info("Stopping worker pool...")
                self.worker_pool.stop_workers()
            
            # 4. Cleanup analysis service
            if self.analysis_service:
                logger.info("Cleaning up analysis service...")
                self.analysis_service.cleanup()
            
            # 5. Wait for health monitor to stop
            if self.health_monitor_thread and self.health_monitor_thread.is_alive():
                self.health_monitor_thread.join(timeout=5.0)
            
            # Log final statistics
            self._log_final_statistics()
            
            logger.info("Processor shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _log_final_statistics(self):
        """Log final system statistics before shutdown"""
        try:
            logger.info("=== Final System Statistics ===")
            
            uptime_hours = self.system_stats['uptime'] / 3600.0
            logger.info(f"Total Uptime: {uptime_hours:.2f} hours")
            logger.info(f"Total Violations Processed: {self.system_stats['total_violations_processed']}")
            
            if self.worker_pool:
                pool_stats = self.worker_pool.get_pool_stats()
                logger.info(f"Total Tasks Processed: {pool_stats.total_processed}")
                logger.info(f"Total Tasks Failed: {pool_stats.total_failed}")
                logger.info(f"Average Processing Time: {pool_stats.avg_processing_time:.3f}s")
            
            if self.monitoring_service:
                monitoring_stats = self.monitoring_service.get_monitoring_stats()
                total_frames = sum(
                    stream.get('frames_processed', 0) 
                    for stream in monitoring_stats.get('streams', {}).values()
                )
                logger.info(f"Total Frames Processed: {total_frames}")
            
            logger.info("=== End Final Statistics ===")
            
        except Exception as e:
            logger.error(f"Error logging final statistics: {e}")
    
    def get_system_health(self) -> SystemHealth:
        """Get overall system health status"""
        try:
            # Determine system status
            if not self.is_running:
                status = "critical"
                message = "System not running"
            elif not self.monitoring_service or not self.monitoring_service.is_monitoring:
                status = "critical"
                message = "Monitoring service not active"
            elif not self.worker_pool or not self.worker_pool.is_running:
                status = "critical"
                message = "Worker pool not active"
            else:
                # Check component health
                pool_health = self.worker_pool.get_health_summary()
                
                if pool_health['pool_status'] == 'critical':
                    status = "critical"
                    message = f"Worker pool critical: {pool_health['pool_message']}"
                elif pool_health['pool_status'] == 'warning':
                    status = "warning"
                    message = f"Worker pool warning: {pool_health['pool_message']}"
                else:
                    status = "healthy"
                    message = "All components operating normally"
            
            # Collect metrics
            metrics = self.system_stats.copy()
            if self.worker_pool:
                pool_stats = self.worker_pool.get_pool_stats()
                metrics.update({
                    'active_workers': pool_stats.active_workers,
                    'queue_size': pool_stats.queue_size,
                    'total_processed': pool_stats.total_processed,
                    'throughput_per_minute': pool_stats.throughput_per_minute
                })
            
            return SystemHealth(
                component="illegal-parking-processor",
                status=status,
                message=message,
                metrics=metrics
            )
            
        except Exception as e:
            return SystemHealth(
                component="illegal-parking-processor",
                status="critical",
                message=f"Error checking health: {e}"
            )


# Global processor instance
processor = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global processor
    
    signal_names = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}
    signal_name = signal_names.get(signum, f"Signal {signum}")
    
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    
    if processor:
        # Create shutdown task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(processor.shutdown())
        finally:
            loop.close()
    
    sys.exit(0)


async def main():
    """Main entry point for the standalone processor"""
    global processor
    
    try:
        logger.info("Starting Illegal Parking Detection System")
        logger.info("=" * 60)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and initialize processor
        processor = IllegalParkingProcessor()
        
        # Start the processor
        if await processor.start():
            # Run main processing loop
            await processor.run_main_loop()
        else:
            logger.error("Failed to start processor")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        if processor:
            await processor.shutdown()


if __name__ == "__main__":
    """
    Main entry point for the standalone AI processor.
    
    Usage:
        python main.py
    
    The processor will:
    1. Load multi-YAML configuration
    2. Initialize AI components
    3. Start two-phase processing (monitoring + analysis)
    4. Run until interrupted or shut down gracefully
    """
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)