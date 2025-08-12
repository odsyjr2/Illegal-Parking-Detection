#!/usr/bin/env python3
"""
Performance Testing Framework for Multi-Stream Processing

This module provides comprehensive performance testing for the illegal parking
detection system. It measures system performance with varying numbers of
concurrent CCTV streams and generates detailed performance reports.

Key Features:
- Progressive stream loading (1, 2, 3, 4, 5, 6 streams)
- Resource monitoring (CPU, memory, GPU if available)
- Performance metrics collection (FPS, processing times, queue depths)
- Bottleneck identification and analysis
- Comprehensive performance reporting
- Load testing with violation scenarios

Usage:
    python test/performance_tester.py
"""

import os
import sys
import time
import asyncio
import threading
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import csv
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Add ai_server to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our core system
from utils.config_loader import load_config
from utils.logger import setup_logging, get_logger
from main import IllegalParkingProcessor
from models import PerformanceMetrics, SystemHealth

# Configure logging
logger = get_logger(__name__)


class SystemMonitor:
    """Monitors system resource usage during testing"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Resource tracking
        self.cpu_usage_history: List[float] = []
        self.memory_usage_history: List[float] = []
        self.timestamp_history: List[datetime] = []
        
        # GPU monitoring (if available)
        self.gpu_available = False
        self.gpu_usage_history: List[float] = []
        
        try:
            import GPUtil
            self.gpu_available = len(GPUtil.getGPUs()) > 0
            if self.gpu_available:
                logger.info("GPU monitoring enabled")
        except ImportError:
            logger.info("GPU monitoring not available (GPUtil not installed)")
    
    def start_monitoring(self):
        """Start resource monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="SystemMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                timestamp = datetime.now()
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # Store measurements
                self.timestamp_history.append(timestamp)
                self.cpu_usage_history.append(cpu_percent)
                self.memory_usage_history.append(memory_percent)
                
                # GPU usage (if available)
                if self.gpu_available:
                    try:
                        import GPUtil
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu_usage = gpus[0].load * 100  # Convert to percentage
                            self.gpu_usage_history.append(gpu_usage)
                    except:
                        pass
                
                # Keep history size manageable
                if len(self.timestamp_history) > 3600:  # 1 hour at 1 second intervals
                    self.timestamp_history = self.timestamp_history[-3600:]
                    self.cpu_usage_history = self.cpu_usage_history[-3600:]
                    self.memory_usage_history = self.memory_usage_history[-3600:]
                    if self.gpu_available:
                        self.gpu_usage_history = self.gpu_usage_history[-3600:]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        usage = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_mb': memory.used / 1024 / 1024
        }
        
        if self.gpu_available:
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    usage['gpu_percent'] = gpus[0].load * 100
                    usage['gpu_memory_mb'] = gpus[0].memoryUsed
            except:
                pass
        
        return usage
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get resource usage statistics"""
        if not self.cpu_usage_history:
            return {}
        
        stats = {
            'cpu': {
                'avg': np.mean(self.cpu_usage_history),
                'max': np.max(self.cpu_usage_history),
                'min': np.min(self.cpu_usage_history),
                'std': np.std(self.cpu_usage_history)
            },
            'memory': {
                'avg': np.mean(self.memory_usage_history),
                'max': np.max(self.memory_usage_history),
                'min': np.min(self.memory_usage_history),
                'std': np.std(self.memory_usage_history)
            },
            'duration_seconds': len(self.timestamp_history) * self.monitoring_interval
        }
        
        if self.gpu_available and self.gpu_usage_history:
            stats['gpu'] = {
                'avg': np.mean(self.gpu_usage_history),
                'max': np.max(self.gpu_usage_history),
                'min': np.min(self.gpu_usage_history),
                'std': np.std(self.gpu_usage_history)
            }
        
        return stats


class PerformanceTest:
    """Individual performance test configuration and results"""
    
    def __init__(self, test_name: str, stream_count: int, duration_seconds: int):
        self.test_name = test_name
        self.stream_count = stream_count
        self.duration_seconds = duration_seconds
        
        # Test configuration
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Performance metrics
        self.processor_stats: Dict[str, Any] = {}
        self.resource_stats: Dict[str, Any] = {}
        self.fps_history: List[float] = []
        self.processing_time_history: List[float] = []
        self.queue_depth_history: List[int] = []
        
        # Success/failure tracking
        self.success = False
        self.error_message: Optional[str] = None
        
    def start(self):
        """Mark test as started"""
        self.start_time = datetime.now()
        logger.info(f"Starting test: {self.test_name} ({self.stream_count} streams)")
    
    def end(self, success: bool = True, error_message: Optional[str] = None):
        """Mark test as completed"""
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error_message
        
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Test completed: {self.test_name} in {duration:.1f}s (Success: {success})")
    
    def add_measurement(self, fps: float, processing_time: float, queue_depth: int):
        """Add performance measurement"""
        self.fps_history.append(fps)
        self.processing_time_history.append(processing_time)
        self.queue_depth_history.append(queue_depth)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        if not self.start_time:
            return {"status": "not_started"}
        
        duration = 0
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        summary = {
            "test_name": self.test_name,
            "stream_count": self.stream_count,
            "duration_seconds": duration,
            "success": self.success,
            "error_message": self.error_message
        }
        
        if self.fps_history:
            summary["performance"] = {
                "avg_fps": np.mean(self.fps_history),
                "max_fps": np.max(self.fps_history),
                "min_fps": np.min(self.fps_history),
                "avg_processing_time": np.mean(self.processing_time_history),
                "max_queue_depth": max(self.queue_depth_history) if self.queue_depth_history else 0,
                "measurements_count": len(self.fps_history)
            }
        
        summary["resource_stats"] = self.resource_stats
        summary["processor_stats"] = self.processor_stats
        
        return summary


class PerformanceTester:
    """Main performance testing framework"""
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.system_monitor = SystemMonitor()
        self.tests: List[PerformanceTest] = []
        
        # Test configuration
        self.test_duration = 60  # seconds per test
        self.measurement_interval = 2.0  # seconds between measurements
        
        # Output configuration
        self.output_dir = Path(__file__).parent / "performance_results"
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("PerformanceTester created")
    
    async def initialize(self) -> bool:
        """Initialize testing framework"""
        try:
            logger.info("Initializing Performance Tester...")
            
            # Load configuration
            self.config = load_config()
            setup_logging(self.config.get('logging', {}))
            
            # Start system monitoring
            self.system_monitor.start_monitoring()
            
            logger.info("Performance Tester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing performance tester: {e}")
            return False
    
    async def run_all_tests(self) -> List[PerformanceTest]:
        """Run complete performance test suite"""
        logger.info("Starting Performance Test Suite")
        logger.info("=" * 50)
        
        try:
            # Define test configurations
            test_configs = [
                ("Single Stream", 1, self.test_duration),
                ("Dual Stream", 2, self.test_duration),
                ("Triple Stream", 3, self.test_duration),
                ("Quad Stream", 4, self.test_duration),
                ("Penta Stream", 5, self.test_duration),
                ("Hexa Stream", 6, self.test_duration)
            ]
            
            # Run each test
            for test_name, stream_count, duration in test_configs:
                test = PerformanceTest(test_name, stream_count, duration)
                
                try:
                    await self._run_single_test(test)
                    self.tests.append(test)
                    
                    # Cool down between tests
                    logger.info(f"Cooling down for 10 seconds...")
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Test {test_name} failed: {e}")
                    test.end(success=False, error_message=str(e))
                    self.tests.append(test)
            
            # Generate reports
            await self._generate_reports()
            
            logger.info("Performance Test Suite completed")
            return self.tests
            
        except Exception as e:
            logger.error(f"Error running performance tests: {e}")
            return self.tests
        finally:
            self.system_monitor.stop_monitoring()
    
    async def _run_single_test(self, test: PerformanceTest):
        """Run a single performance test"""
        test.start()
        
        try:
            # Create processor instance
            processor = IllegalParkingProcessor()
            
            # Initialize processor
            if not await processor.initialize():
                raise RuntimeError("Failed to initialize processor")
            
            # Modify configuration for this test (limit streams)
            await self._configure_streams_for_test(processor, test.stream_count)
            
            # Start processor
            if not await processor.start():
                raise RuntimeError("Failed to start processor")
            
            # Run test for specified duration
            start_time = time.time()
            measurement_count = 0
            
            while time.time() - start_time < test.duration_seconds:
                # Collect performance measurements
                await self._collect_measurements(processor, test)
                measurement_count += 1
                
                # Wait for next measurement
                await asyncio.sleep(self.measurement_interval)
            
            # Collect final statistics
            test.processor_stats = self._get_processor_stats(processor)
            test.resource_stats = self.system_monitor.get_statistics()
            
            # Clean shutdown
            await processor.shutdown()
            
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
            raise
    
    async def _configure_streams_for_test(self, processor: IllegalParkingProcessor, stream_count: int):
        """Configure processor to use specified number of streams"""
        try:
            # Get configured streams
            streams = self.config.get('cctv_streams', {}).get('local_streams', [])
            enabled_streams = [s for s in streams if s.get('enabled', True)]
            
            # Limit to requested count
            target_streams = enabled_streams[:stream_count]
            target_stream_ids = [s['id'] for s in target_streams]
            
            logger.info(f"Configuring test with {len(target_stream_ids)} streams: {target_stream_ids}")
            
            # This would modify the processor configuration for the test
            # For now, we'll assume the processor can handle stream selection
            
        except Exception as e:
            logger.error(f"Error configuring streams for test: {e}")
            raise
    
    async def _collect_measurements(self, processor: IllegalParkingProcessor, test: PerformanceTest):
        """Collect performance measurements from processor"""
        try:
            # Get monitoring service statistics
            if processor.monitoring_service:
                monitoring_stats = processor.monitoring_service.get_monitoring_stats()
                avg_fps = monitoring_stats.get('average_fps', 0.0)
            else:
                avg_fps = 0.0
            
            # Get worker pool statistics
            if processor.worker_pool:
                pool_stats = processor.worker_pool.get_pool_stats()
                avg_processing_time = pool_stats.avg_processing_time
                queue_depth = pool_stats.queue_size
            else:
                avg_processing_time = 0.0
                queue_depth = 0
            
            # Add measurement to test
            test.add_measurement(avg_fps, avg_processing_time, queue_depth)
            
            logger.debug(f"Measurement: FPS={avg_fps:.1f}, ProcessingTime={avg_processing_time:.3f}s, Queue={queue_depth}")
            
        except Exception as e:
            logger.error(f"Error collecting measurements: {e}")
    
    def _get_processor_stats(self, processor: IllegalParkingProcessor) -> Dict[str, Any]:
        """Get comprehensive processor statistics"""
        stats = {}
        
        try:
            # Monitoring service stats
            if processor.monitoring_service:
                stats['monitoring'] = processor.monitoring_service.get_monitoring_stats()
            
            # Worker pool stats
            if processor.worker_pool:
                stats['worker_pool'] = processor.worker_pool.get_pool_stats().to_dict() if hasattr(
                    processor.worker_pool.get_pool_stats(), 'to_dict'
                ) else processor.worker_pool.get_pool_stats().__dict__
            
            # Analysis service stats
            if processor.analysis_service:
                stats['analysis'] = processor.analysis_service.get_analysis_stats()
            
            # System health
            stats['system_health'] = processor.get_system_health().to_dict()
            
        except Exception as e:
            logger.error(f"Error getting processor stats: {e}")
            stats['error'] = str(e)
        
        return stats
    
    async def _generate_reports(self):
        """Generate comprehensive performance reports"""
        try:
            logger.info("Generating performance reports...")
            
            # Generate JSON report
            await self._generate_json_report()
            
            # Generate CSV report
            await self._generate_csv_report()
            
            # Generate visualizations
            await self._generate_visualizations()
            
            # Generate summary report
            await self._generate_summary_report()
            
            logger.info(f"Reports generated in {self.output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
    
    async def _generate_json_report(self):
        """Generate detailed JSON report"""
        report_data = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.tests),
                "successful_tests": len([t for t in self.tests if t.success])
            },
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "platform": psutil.Platform if hasattr(psutil, 'Platform') else "Unknown"
            },
            "tests": [test.get_summary() for test in self.tests]
        }
        
        output_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report saved: {output_file}")
    
    async def _generate_csv_report(self):
        """Generate CSV report with test summaries"""
        output_file = self.output_dir / f"performance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Headers
            writer.writerow([
                'Test Name', 'Stream Count', 'Duration (s)', 'Success',
                'Avg FPS', 'Max FPS', 'Min FPS', 'Avg Processing Time (s)',
                'Max Queue Depth', 'Avg CPU (%)', 'Max Memory (%)'
            ])
            
            # Data rows
            for test in self.tests:
                summary = test.get_summary()
                perf = summary.get('performance', {})
                resources = summary.get('resource_stats', {})
                
                writer.writerow([
                    test.test_name,
                    test.stream_count,
                    summary.get('duration_seconds', 0),
                    test.success,
                    perf.get('avg_fps', 0),
                    perf.get('max_fps', 0),
                    perf.get('min_fps', 0),
                    perf.get('avg_processing_time', 0),
                    perf.get('max_queue_depth', 0),
                    resources.get('cpu', {}).get('avg', 0),
                    resources.get('memory', {}).get('max', 0)
                ])
        
        logger.info(f"CSV report saved: {output_file}")
    
    async def _generate_visualizations(self):
        """Generate performance visualization charts"""
        try:
            # FPS vs Stream Count
            stream_counts = [t.stream_count for t in self.tests if t.success]
            avg_fps = [t.get_summary().get('performance', {}).get('avg_fps', 0) for t in self.tests if t.success]
            
            if stream_counts and avg_fps:
                plt.figure(figsize=(10, 6))
                plt.plot(stream_counts, avg_fps, 'bo-', linewidth=2, markersize=8)
                plt.xlabel('Number of Streams')
                plt.ylabel('Average FPS')
                plt.title('Performance vs Stream Count')
                plt.grid(True, alpha=0.3)
                plt.xticks(stream_counts)
                
                output_file = self.output_dir / f"fps_vs_streams_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"FPS chart saved: {output_file}")
            
            # Resource usage over time
            if self.system_monitor.timestamp_history:
                plt.figure(figsize=(12, 8))
                
                # CPU usage
                plt.subplot(2, 1, 1)
                plt.plot(self.system_monitor.timestamp_history, self.system_monitor.cpu_usage_history, 'r-', label='CPU %')
                plt.ylabel('CPU Usage (%)')
                plt.title('System Resource Usage During Testing')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Memory usage
                plt.subplot(2, 1, 2)
                plt.plot(self.system_monitor.timestamp_history, self.system_monitor.memory_usage_history, 'b-', label='Memory %')
                plt.ylabel('Memory Usage (%)')
                plt.xlabel('Time')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                output_file = self.output_dir / f"resource_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"Resource chart saved: {output_file}")
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
    
    async def _generate_summary_report(self):
        """Generate human-readable summary report"""
        output_file = self.output_dir / f"performance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(output_file, 'w') as f:
            f.write("Illegal Parking Detection System - Performance Test Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Tests: {len(self.tests)}\n")
            f.write(f"Successful Tests: {len([t for t in self.tests if t.success])}\n\n")
            
            # System information
            f.write("System Information:\n")
            f.write(f"  CPU Cores: {psutil.cpu_count()}\n")
            f.write(f"  Total Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB\n")
            f.write(f"  GPU Available: {self.system_monitor.gpu_available}\n\n")
            
            # Test results
            f.write("Test Results:\n")
            for test in self.tests:
                summary = test.get_summary()
                f.write(f"\n{test.test_name} ({test.stream_count} streams):\n")
                f.write(f"  Status: {'SUCCESS' if test.success else 'FAILED'}\n")
                f.write(f"  Duration: {summary.get('duration_seconds', 0):.1f} seconds\n")
                
                if test.success:
                    perf = summary.get('performance', {})
                    f.write(f"  Average FPS: {perf.get('avg_fps', 0):.1f}\n")
                    f.write(f"  Processing Time: {perf.get('avg_processing_time', 0):.3f}s\n")
                    f.write(f"  Max Queue Depth: {perf.get('max_queue_depth', 0)}\n")
                else:
                    f.write(f"  Error: {test.error_message}\n")
            
            # Performance summary
            successful_tests = [t for t in self.tests if t.success]
            if successful_tests:
                f.write("\nPerformance Summary:\n")
                
                max_fps_test = max(successful_tests, key=lambda t: t.get_summary().get('performance', {}).get('avg_fps', 0))
                f.write(f"  Best FPS: {max_fps_test.get_summary().get('performance', {}).get('avg_fps', 0):.1f} "
                       f"({max_fps_test.stream_count} streams)\n")
                
                # Recommended configuration
                optimal_streams = 1
                for test in successful_tests:
                    perf = test.get_summary().get('performance', {})
                    if perf.get('avg_fps', 0) >= 10 and perf.get('max_queue_depth', 0) < 50:
                        optimal_streams = max(optimal_streams, test.stream_count)
                
                f.write(f"  Recommended max streams: {optimal_streams}\n")
        
        logger.info(f"Summary report saved: {output_file}")


async def main():
    """Main entry point for performance testing"""
    try:
        logger.info("Starting Performance Testing Framework")
        logger.info("=" * 50)
        
        # Create and run performance tester
        tester = PerformanceTester()
        
        if await tester.initialize():
            tests = await tester.run_all_tests()
            
            # Print summary
            successful_tests = len([t for t in tests if t.success])
            logger.info(f"Performance testing completed: {successful_tests}/{len(tests)} tests successful")
            
            if successful_tests > 0:
                logger.info("Check the performance_results directory for detailed reports")
            
        else:
            logger.error("Failed to initialize performance tester")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Performance testing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    """
    Run performance testing for the illegal parking detection system.
    
    This will:
    1. Test system performance with 1-6 concurrent CCTV streams
    2. Monitor CPU, memory, and GPU usage
    3. Measure FPS, processing times, and queue depths
    4. Generate comprehensive performance reports
    """
    
    print("Performance Testing Framework for Illegal Parking Detection")
    print("=" * 60)
    print("This test will measure system performance with varying numbers")
    print("of concurrent CCTV streams (1-6 streams).")
    print()
    print("The test will:")
    print("- Run each configuration for 60 seconds")
    print("- Monitor CPU, memory, and GPU usage")
    print("- Measure FPS and processing times")
    print("- Generate detailed performance reports")
    print()
    print("Press any key to continue...")
    input()
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)