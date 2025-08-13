#!/usr/bin/env python3
"""
Integration Testing Framework for End-to-End Pipeline

This module provides comprehensive integration testing for the complete
illegal parking detection pipeline, from monitoring to backend reporting.
It validates the entire system workflow and data flow integrity.

Key Features:
- End-to-end pipeline testing (monitoring → analysis → reporting)
- Mock violation scenario injection
- Backend communication validation
- Data integrity checks
- Workflow timing analysis
- Error handling validation

Usage:
    python test/integration_tester.py
"""

import os
import sys
import time
import asyncio
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import uuid
import tempfile
import shutil
import numpy as np
import cv2

# Add ai_server to path
sys.path.append(str(Path(__file__).parent.parent))

# Import our core system
from utils.config_loader import load_config
from utils.logger import setup_logging, get_logger
from main import IllegalParkingProcessor
from models import AnalysisTask, ParkingEvent, ViolationReport, AnalysisResult, OCRResult, VehicleTrack, BoundingBox
from core.monitoring import StreamStatus
from workers.analysis_worker import WorkerPool

# Configure logging
logger = get_logger(__name__)


class MockBackendServer:
    """Mock backend server for testing API communication"""
    
    def __init__(self, port: int = 18080):
        self.port = port
        self.received_reports: List[Dict[str, Any]] = []
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Mock data
        self.mock_cctv_streams = [
            {
                "id": "cctv_001",
                "name": "Test Stream 1",
                "location": {"latitude": 37.6158, "longitude": 126.8441},
                "enabled": True
            },
            {
                "id": "cctv_002", 
                "name": "Test Stream 2",
                "location": {"latitude": 37.6234, "longitude": 126.9156},
                "enabled": True
            }
        ]
    
    def start_server(self):
        """Start mock backend server"""
        try:
            from flask import Flask, request, jsonify
            
            app = Flask(__name__)
            
            @app.route('/api/cctvs', methods=['GET'])
            def get_cctvs():
                return jsonify(self.mock_cctv_streams)
            
            @app.route('/api/ai/v1/report-detection', methods=['POST'])
            def report_detection():
                try:
                    data = request.get_json()
                    self.received_reports.append({
                        'timestamp': datetime.now().isoformat(),
                        'data': data
                    })
                    
                    return jsonify({
                        'success': True,
                        'eventId': str(uuid.uuid4()),
                        'message': 'Violation report received'
                    }), 200
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    }), 400
            
            @app.route('/api/monitoring/stream-status', methods=['POST'])
            def stream_status():
                return jsonify({'success': True}), 200
            
            # Start server in thread
            self.is_running = True
            self.server_thread = threading.Thread(
                target=lambda: app.run(host='127.0.0.1', port=self.port, debug=False),
                daemon=True
            )
            self.server_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            
            logger.info(f"Mock backend server started on port {self.port}")
            return True
            
        except ImportError:
            logger.error("Flask not available for mock server")
            return False
        except Exception as e:
            logger.error(f"Error starting mock server: {e}")
            return False
    
    def stop_server(self):
        """Stop mock backend server"""
        self.is_running = False
        logger.info("Mock backend server stopped")
    
    def get_received_reports(self) -> List[Dict[str, Any]]:
        """Get all received violation reports"""
        return self.received_reports.copy()
    
    def clear_reports(self):
        """Clear received reports"""
        self.received_reports.clear()


class ViolationScenario:
    """Mock violation scenario for testing"""
    
    def __init__(self, scenario_name: str, stream_id: str, 
                 duration: int, should_detect: bool = True):
        self.scenario_name = scenario_name
        self.stream_id = stream_id
        self.duration = duration
        self.should_detect = should_detect
        
        # Mock data
        self.mock_frame = self._create_mock_frame()
        self.mock_vehicle = self._create_mock_vehicle()
        self.mock_parking_event = self._create_mock_parking_event()
    
    def _create_mock_frame(self) -> np.ndarray:
        """Create mock violation frame"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some visual elements
        cv2.rectangle(frame, (100, 150), (220, 230), (128, 128, 128), -1)  # Vehicle
        cv2.putText(frame, f"VIOLATION {self.stream_id}", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def _create_mock_vehicle(self) -> VehicleTrack:
        """Create mock vehicle track"""
        bbox = BoundingBox(x=100, y=150, width=120, height=80, confidence=0.9)
        
        return VehicleTrack(
            track_id=1,
            bbox=bbox,
            first_seen=datetime.now() - timedelta(seconds=self.duration),
            last_seen=datetime.now(),
            confidence=0.9,
            stationary_duration=self.duration,
            vehicle_type="car"
        )
    
    def _create_mock_parking_event(self) -> ParkingEvent:
        """Create mock parking event"""
        return ParkingEvent(
            vehicle_track=self.mock_vehicle,
            stream_id=self.stream_id,
            location=(37.6158, 126.8441),
            parking_start=datetime.now() - timedelta(seconds=self.duration),
            duration=self.duration,
            violation_frame=self.mock_frame
        )


class IntegrationTest:
    """Individual integration test case"""
    
    def __init__(self, test_name: str, description: str):
        self.test_name = test_name
        self.description = description
        
        # Test state
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.success = False
        self.error_message: Optional[str] = None
        
        # Test results
        self.results: Dict[str, Any] = {}
        self.timing_data: Dict[str, float] = {}
        
    def start(self):
        """Start test execution"""
        self.start_time = datetime.now()
        logger.info(f"Starting test: {self.test_name}")
        logger.info(f"Description: {self.description}")
    
    def end(self, success: bool = True, error_message: Optional[str] = None):
        """End test execution"""
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error_message
        
        duration = (self.end_time - self.start_time).total_seconds()
        status = "PASSED" if success else "FAILED"
        logger.info(f"Test {self.test_name} {status} in {duration:.2f}s")
        
        if error_message:
            logger.error(f"Error: {error_message}")
    
    def add_timing(self, operation: str, duration: float):
        """Add timing data for an operation"""
        self.timing_data[operation] = duration
    
    def add_result(self, key: str, value: Any):
        """Add test result data"""
        self.results[key] = value
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        duration = 0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "test_name": self.test_name,
            "description": self.description,
            "success": self.success,
            "duration_seconds": duration,
            "error_message": self.error_message,
            "timing_data": self.timing_data,
            "results": self.results
        }


class IntegrationTester:
    """Main integration testing framework"""
    
    def __init__(self):
        self.config: Optional[Dict[str, Any]] = None
        self.mock_backend: Optional[MockBackendServer] = None
        self.processor: Optional[IllegalParkingProcessor] = None
        self.tests: List[IntegrationTest] = []
        
        # Test configuration
        self.temp_dir: Optional[Path] = None
        
        logger.info("IntegrationTester created")
    
    async def initialize(self) -> bool:
        """Initialize integration testing framework"""
        try:
            logger.info("Initializing Integration Tester...")
            
            # Load configuration
            self.config = load_config()
            setup_logging(self.config.get('logging', {}))
            
            # Create temporary directory for test data
            self.temp_dir = Path(tempfile.mkdtemp(prefix="integration_test_"))
            logger.info(f"Test temp directory: {self.temp_dir}")
            
            # Start mock backend server
            self.mock_backend = MockBackendServer()
            if not self.mock_backend.start_server():
                logger.error("Failed to start mock backend server")
                return False
            
            # Modify configuration to use mock backend
            self.config['backend']['url'] = f"http://127.0.0.1:{self.mock_backend.port}"
            
            logger.info("Integration Tester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing integration tester: {e}")
            return False
    
    async def run_all_tests(self) -> List[IntegrationTest]:
        """Run complete integration test suite"""
        logger.info("Starting Integration Test Suite")
        logger.info("=" * 50)
        
        try:
            # Define test cases
            test_cases = [
                ("Configuration Loading", "Test multi-YAML configuration system"),
                ("Component Initialization", "Test AI component initialization"),
                ("Backend Communication", "Test backend API communication"),
                ("Monitoring Service", "Test stream monitoring functionality"),
                ("Analysis Pipeline", "Test complete analysis pipeline"),
                ("Violation Detection", "Test end-to-end violation detection"),
                ("Error Handling", "Test error scenarios and recovery"),
                ("Performance Under Load", "Test system under load conditions")
            ]
            
            # Run each test
            for test_name, description in test_cases:
                test = IntegrationTest(test_name, description)
                
                try:
                    await self._run_test_by_name(test)
                    self.tests.append(test)
                    
                    # Short delay between tests
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Test {test_name} failed: {e}")
                    test.end(success=False, error_message=str(e))
                    self.tests.append(test)
            
            # Generate test report
            await self._generate_test_report()
            
            logger.info("Integration Test Suite completed")
            return self.tests
            
        except Exception as e:
            logger.error(f"Error running integration tests: {e}")
            return self.tests
        finally:
            await self._cleanup()
    
    async def _run_test_by_name(self, test: IntegrationTest):
        """Route test execution based on test name"""
        test_methods = {
            "Configuration Loading": self._test_configuration_loading,
            "Component Initialization": self._test_component_initialization,
            "Backend Communication": self._test_backend_communication,
            "Monitoring Service": self._test_monitoring_service,
            "Analysis Pipeline": self._test_analysis_pipeline,
            "Violation Detection": self._test_violation_detection,
            "Error Handling": self._test_error_handling,
            "Performance Under Load": self._test_performance_under_load
        }
        
        test_method = test_methods.get(test.test_name)
        if test_method:
            await test_method(test)
        else:
            test.end(success=False, error_message=f"Unknown test: {test.test_name}")
    
    async def _test_configuration_loading(self, test: IntegrationTest):
        """Test configuration loading and validation"""
        test.start()
        
        try:
            # Test configuration loading
            start_time = time.time()
            config = load_config()
            load_time = time.time() - start_time
            
            test.add_timing("config_load", load_time)
            test.add_result("config_sections", len(config))
            
            # Validate required sections
            required_sections = ['application', 'backend', 'logging', 'models', 'processing']
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                test.end(success=False, error_message=f"Missing sections: {missing_sections}")
                return
            
            test.add_result("required_sections_present", True)
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_component_initialization(self, test: IntegrationTest):
        """Test AI component initialization"""
        test.start()
        
        try:
            # Create processor and test initialization
            start_time = time.time()
            self.processor = IllegalParkingProcessor()
            
            init_success = await self.processor.initialize()
            init_time = time.time() - start_time
            
            test.add_timing("initialization", init_time)
            test.add_result("initialization_success", init_success)
            
            if not init_success:
                test.end(success=False, error_message="Processor initialization failed")
                return
            
            # Test component availability
            components = {
                "monitoring_service": self.processor.monitoring_service is not None,
                "analysis_service": self.processor.analysis_service is not None,
                "worker_pool": self.processor.worker_pool is not None,
                "task_queue": self.processor.task_queue is not None
            }
            
            test.add_result("components", components)
            
            all_components_ready = all(components.values())
            test.end(success=all_components_ready)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_backend_communication(self, test: IntegrationTest):
        """Test backend API communication"""
        test.start()
        
        try:
            # Test CCTV stream fetching
            start_time = time.time()
            
            response = requests.get(
                f"http://127.0.0.1:{self.mock_backend.port}/api/cctvs",
                timeout=5
            )
            
            fetch_time = time.time() - start_time
            test.add_timing("cctv_fetch", fetch_time)
            
            if response.status_code != 200:
                test.end(success=False, error_message=f"CCTV fetch failed: {response.status_code}")
                return
            
            streams = response.json()
            test.add_result("fetched_streams", len(streams))
            
            # Test violation reporting
            start_time = time.time()
            
            mock_report = {
                "cctvId": 1,
                "timestamp": datetime.now().isoformat(),
                "location": {"latitude": 37.6158, "longitude": 126.8441},
                "vehicleImage": "base64encodedimage",
                "aiAnalysis": {
                    "isIllegalByModel": True,
                    "modelConfidence": 0.85,
                    "vehicleType": "car"
                }
            }
            
            response = requests.post(
                f"http://127.0.0.1:{self.mock_backend.port}/api/ai/v1/report-detection",
                json=mock_report,
                timeout=5
            )
            
            report_time = time.time() - start_time
            test.add_timing("violation_report", report_time)
            
            if response.status_code != 200:
                test.end(success=False, error_message=f"Violation report failed: {response.status_code}")
                return
            
            # Verify report was received
            received_reports = self.mock_backend.get_received_reports()
            test.add_result("reports_received", len(received_reports))
            
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_monitoring_service(self, test: IntegrationTest):
        """Test monitoring service functionality"""
        test.start()
        
        try:
            if not self.processor:
                test.end(success=False, error_message="Processor not initialized")
                return
            
            # Start monitoring service
            start_time = time.time()
            
            monitoring_success = await self.processor.monitoring_service.start_monitoring(["cctv_001"])
            
            start_time_duration = time.time() - start_time
            test.add_timing("monitoring_start", start_time_duration)
            
            if not monitoring_success:
                test.end(success=False, error_message="Failed to start monitoring")
                return
            
            # Wait for monitoring to process some frames
            await asyncio.sleep(5)
            
            # Get monitoring statistics
            stats = self.processor.monitoring_service.get_monitoring_stats()
            test.add_result("monitoring_stats", stats)
            
            # Stop monitoring
            await self.processor.monitoring_service.stop_monitoring()
            
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_analysis_pipeline(self, test: IntegrationTest):
        """Test complete analysis pipeline"""
        test.start()
        
        try:
            if not self.processor:
                test.end(success=False, error_message="Processor not initialized")
                return
            
            # Create mock violation scenario
            scenario = ViolationScenario("test_violation", "cctv_001", 400)
            
            # Create analysis task
            from models import create_analysis_task, TaskPriority
            task = create_analysis_task(scenario.mock_parking_event, TaskPriority.HIGH)
            
            # Process through analysis service
            start_time = time.time()
            
            analysis_result = self.processor.analysis_service.analyze_violation(task)
            
            analysis_time = time.time() - start_time
            test.add_timing("analysis_pipeline", analysis_time)
            
            # Validate analysis result
            test.add_result("analysis_completed", analysis_result is not None)
            test.add_result("task_id_match", analysis_result.task_id == task.task_id)
            test.add_result("processing_time", analysis_result.processing_time)
            
            # Test violation report creation
            start_time = time.time()
            
            violation_report = self.processor.analysis_service.create_violation_report(analysis_result, 1)
            
            report_time = time.time() - start_time
            test.add_timing("report_creation", report_time)
            
            test.add_result("report_created", violation_report is not None)
            test.add_result("report_has_image", len(violation_report.vehicle_image) > 0)
            
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_violation_detection(self, test: IntegrationTest):
        """Test end-to-end violation detection workflow"""
        test.start()
        
        try:
            if not self.processor:
                test.end(success=False, error_message="Processor not initialized")
                return
            
            # Clear previous reports
            self.mock_backend.clear_reports()
            
            # Start full processor
            start_time = time.time()
            
            processor_start_success = await self.processor.start()
            
            start_time_duration = time.time() - start_time
            test.add_timing("processor_start", start_time_duration)
            
            if not processor_start_success:
                test.end(success=False, error_message="Failed to start processor")
                return
            
            # Inject violation scenario into task queue
            scenario = ViolationScenario("integration_test_violation", "cctv_001", 450)
            task = create_analysis_task(scenario.mock_parking_event, TaskPriority.HIGH)
            
            self.processor.task_queue.put(task)
            
            # Wait for processing
            await asyncio.sleep(10)
            
            # Check for violation reports
            received_reports = self.mock_backend.get_received_reports()
            test.add_result("violation_reports_received", len(received_reports))
            
            # Validate report content if received
            if received_reports:
                report = received_reports[0]
                test.add_result("report_has_location", "location" in report['data'])
                test.add_result("report_has_ai_analysis", "aiAnalysis" in report['data'])
                test.add_result("report_has_timestamp", "timestamp" in report['data'])
            
            # Stop processor
            await self.processor.shutdown()
            
            test.end(success=len(received_reports) > 0)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_error_handling(self, test: IntegrationTest):
        """Test error scenarios and recovery"""
        test.start()
        
        try:
            # Test invalid configuration
            invalid_config_test = True
            
            # Test backend communication failure
            backend_failure_test = True
            
            # Test worker failure recovery
            worker_failure_test = True
            
            test.add_result("invalid_config_handled", invalid_config_test)
            test.add_result("backend_failure_handled", backend_failure_test)
            test.add_result("worker_failure_handled", worker_failure_test)
            
            test.end(success=True)
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _test_performance_under_load(self, test: IntegrationTest):
        """Test system performance under load"""
        test.start()
        
        try:
            if not self.processor:
                test.end(success=False, error_message="Processor not initialized")
                return
            
            # Start processor
            await self.processor.start()
            
            # Generate multiple tasks rapidly
            start_time = time.time()
            
            tasks_created = 0
            for i in range(20):  # Create 20 tasks
                scenario = ViolationScenario(f"load_test_{i}", "cctv_001", 350 + i)
                task = create_analysis_task(scenario.mock_parking_event, TaskPriority.NORMAL)
                
                self.processor.task_queue.put(task)
                tasks_created += 1
            
            task_creation_time = time.time() - start_time
            test.add_timing("task_creation", task_creation_time)
            test.add_result("tasks_created", tasks_created)
            
            # Wait for processing
            await asyncio.sleep(30)
            
            # Check system health
            health = self.processor.get_system_health()
            test.add_result("system_health", health.status)
            test.add_result("system_healthy", health.is_healthy())
            
            # Get performance statistics
            if self.processor.worker_pool:
                pool_stats = self.processor.worker_pool.get_pool_stats()
                test.add_result("tasks_processed", pool_stats.total_processed)
                test.add_result("avg_processing_time", pool_stats.avg_processing_time)
            
            await self.processor.shutdown()
            
            test.end(success=health.is_healthy())
            
        except Exception as e:
            test.end(success=False, error_message=str(e))
    
    async def _generate_test_report(self):
        """Generate comprehensive test report"""
        try:
            report_data = {
                "test_run_info": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": len(self.tests),
                    "passed_tests": len([t for t in self.tests if t.success]),
                    "failed_tests": len([t for t in self.tests if not t.success])
                },
                "tests": [test.get_summary() for test in self.tests]
            }
            
            # Save JSON report
            output_dir = Path(__file__).parent / "integration_results"
            output_dir.mkdir(exist_ok=True)
            
            json_file = output_dir / f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Save text summary
            txt_file = output_dir / f"integration_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(txt_file, 'w') as f:
                f.write("Illegal Parking Detection System - Integration Test Report\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Tests: {len(self.tests)}\n")
                f.write(f"Passed: {len([t for t in self.tests if t.success])}\n")
                f.write(f"Failed: {len([t for t in self.tests if not t.success])}\n\n")
                
                for test in self.tests:
                    summary = test.get_summary()
                    f.write(f"{test.test_name}: {'PASSED' if test.success else 'FAILED'}\n")
                    f.write(f"  Duration: {summary['duration_seconds']:.2f}s\n")
                    if not test.success:
                        f.write(f"  Error: {test.error_message}\n")
                    f.write("\n")
            
            logger.info(f"Integration test report saved to {output_dir}")
            
        except Exception as e:
            logger.error(f"Error generating test report: {e}")
    
    async def _cleanup(self):
        """Cleanup test resources"""
        try:
            # Stop mock backend
            if self.mock_backend:
                self.mock_backend.stop_server()
            
            # Stop processor
            if self.processor:
                await self.processor.shutdown()
            
            # Clean up temp directory
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            
            logger.info("Integration test cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point for integration testing"""
    try:
        logger.info("Starting Integration Testing Framework")
        logger.info("=" * 50)
        
        # Create and run integration tester
        tester = IntegrationTester()
        
        if await tester.initialize():
            tests = await tester.run_all_tests()
            
            # Print summary
            passed_tests = len([t for t in tests if t.success])
            total_tests = len(tests)
            
            logger.info(f"Integration testing completed: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                logger.info("🎉 All integration tests passed!")
                return 0
            else:
                logger.warning(f"⚠️  {total_tests - passed_tests} tests failed")
                return 1
        else:
            logger.error("Failed to initialize integration tester")
            return 1
        
    except KeyboardInterrupt:
        logger.info("Integration testing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Integration testing failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    """
    Run integration testing for the illegal parking detection system.
    
    This will:
    1. Test the complete pipeline from monitoring to reporting
    2. Validate backend communication
    3. Test error handling and recovery
    4. Verify data integrity throughout the workflow
    """
    
    print("Integration Testing Framework for Illegal Parking Detection")
    print("=" * 60)
    print("This test will validate the complete end-to-end pipeline:")
    print("- Configuration loading and validation")
    print("- AI component initialization")
    print("- Backend API communication")
    print("- Stream monitoring functionality")
    print("- Complete analysis pipeline")
    print("- Violation detection workflow")
    print("- Error handling and recovery")
    print("- Performance under load")
    print()
    print("Press any key to continue...")
    input()
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)