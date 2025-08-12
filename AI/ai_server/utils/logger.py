"""
Centralized Logging System for AI Processor

This module provides a centralized logging system with:
- Component-specific loggers
- File rotation and management
- Performance logging capabilities
- Configuration-driven setup
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if hasattr(record, 'color_message'):
            return super().format(record)
            
        # Add color to log level
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            
        return super().format(record)


class PerformanceLogger:
    """Logger for performance metrics and timing"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers: Dict[str, float] = {}
        
    def start_timer(self, operation: str) -> None:
        """Start timing an operation"""
        self._timers[operation] = datetime.now().timestamp()
        
    def end_timer(self, operation: str, details: Optional[str] = None) -> float:
        """End timing and log the duration"""
        if operation not in self._timers:
            self.logger.warning(f"Timer '{operation}' was not started")
            return 0.0
            
        duration = datetime.now().timestamp() - self._timers[operation]
        del self._timers[operation]
        
        message = f"Performance: {operation} took {duration:.3f}s"
        if details:
            message += f" - {details}"
            
        self.logger.info(message)
        return duration
        
    def log_memory_usage(self, component: str, memory_mb: float) -> None:
        """Log memory usage for a component"""
        self.logger.info(f"Memory: {component} using {memory_mb:.1f}MB")
        
    def log_fps(self, stream_id: str, fps: float) -> None:
        """Log FPS for a stream"""
        self.logger.info(f"FPS: {stream_id} processing at {fps:.1f} FPS")


class AIProcessorLogger:
    """
    Centralized logging system for AI Processor.
    
    Provides component-specific loggers with consistent formatting,
    file rotation, and performance logging capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the logging system.
        
        Args:
            config: Logging configuration from config.yaml
        """
        self.config = config
        self.loggers: Dict[str, logging.Logger] = {}
        self.performance_loggers: Dict[str, PerformanceLogger] = {}
        self._setup_formatters()
        self._setup_handlers()
        self._setup_component_loggers()
        
    def _setup_formatters(self) -> None:
        """Setup log formatting patterns"""
        log_format = self.config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Console formatter (with colors if enabled)
        if self.config.get("console_output", {}).get("colored", True):
            self.console_formatter = ColoredFormatter(log_format)
        else:
            self.console_formatter = logging.Formatter(log_format)
            
        # File formatter (no colors)
        self.file_formatter = logging.Formatter(log_format)
        
        # Performance formatter
        self.performance_formatter = logging.Formatter(
            "%(asctime)s - PERFORMANCE - %(message)s"
        )
        
    def _setup_handlers(self) -> None:
        """Setup console and file handlers"""
        self.handlers = {}
        
        # Console handler
        console_config = self.config.get("console_output", {})
        if console_config.get("enabled", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.console_formatter)
            self.handlers["console"] = console_handler
            
        # File handler with rotation
        file_config = self.config.get("file_logging", {})
        if file_config.get("enabled", True):
            log_path = Path(file_config.get("path", "../data/outputs/ai_processor.log"))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            max_size_mb = file_config.get("max_size_mb", 100)
            backup_count = file_config.get("backup_count", 5)
            
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(self.file_formatter)
            self.handlers["file"] = file_handler
            
        # Performance log handler (separate file)
        perf_path = log_path.parent / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_path,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3
        )
        perf_handler.setFormatter(self.performance_formatter)
        self.handlers["performance"] = perf_handler
        
    def _setup_component_loggers(self) -> None:
        """Setup component-specific loggers"""
        # Get component-specific log levels
        component_levels = self.config.get("component_levels", {})
        default_level = self.config.get("level", "INFO")
        
        # Define component logger configurations
        components = [
            "monitoring",      # Phase 1 monitoring service
            "analysis",        # Phase 2 analysis service
            "workers",         # Analysis worker threads
            "config",          # Configuration loading
            "backend",         # Backend communication
            "performance",     # Performance monitoring
            "models",          # AI model operations
            "streams",         # Stream management
            "main"            # Main application
        ]
        
        for component in components:
            logger = self._create_component_logger(
                component, 
                component_levels.get(component, default_level)
            )
            self.loggers[component] = logger
            
            # Create performance logger for components that need it
            if component in ["monitoring", "analysis", "workers", "performance"]:
                self.performance_loggers[component] = PerformanceLogger(logger)
                
    def _create_component_logger(self, name: str, level: str) -> logging.Logger:
        """
        Create a logger for a specific component.
        
        Args:
            name: Component name
            level: Log level string
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"ai_processor.{name}")
        logger.setLevel(getattr(logging, level.upper()))
        logger.propagate = False  # Don't propagate to root logger
        
        # Add handlers to logger
        for handler_name, handler in self.handlers.items():
            if handler_name == "performance" and name != "performance":
                continue  # Only performance logger gets performance handler
            logger.addHandler(handler)
            
        return logger
        
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a component-specific logger.
        
        Args:
            name: Component name
            
        Returns:
            Logger instance
        """
        if name not in self.loggers:
            # Create logger for unknown component with default settings
            default_level = self.config.get("level", "INFO")
            logger = self._create_component_logger(name, default_level)
            self.loggers[name] = logger
            
        return self.loggers[name]
        
    def get_performance_logger(self, name: str) -> PerformanceLogger:
        """
        Get a performance logger for a component.
        
        Args:
            name: Component name
            
        Returns:
            PerformanceLogger instance
        """
        if name not in self.performance_loggers:
            logger = self.get_logger(name)
            self.performance_loggers[name] = PerformanceLogger(logger)
            
        return self.performance_loggers[name]
        
    def log_startup(self, component: str, details: str = "") -> None:
        """Log component startup information"""
        logger = self.get_logger(component)
        message = f"Starting {component}"
        if details:
            message += f": {details}"
        logger.info(message)
        
    def log_shutdown(self, component: str, details: str = "") -> None:
        """Log component shutdown information"""
        logger = self.get_logger(component)
        message = f"Shutting down {component}"
        if details:
            message += f": {details}"
        logger.info(message)
        
    def log_error_with_context(self, component: str, error: Exception, context: str = "") -> None:
        """Log error with full context information"""
        logger = self.get_logger(component)
        message = f"Error in {component}: {str(error)}"
        if context:
            message += f" (Context: {context})"
        logger.error(message, exc_info=True)
        
    def log_configuration_loaded(self, file_name: str, sections: list) -> None:
        """Log configuration file loading"""
        logger = self.get_logger("config")
        logger.info(f"Loaded {file_name} with sections: {', '.join(sections)}")
        
    def log_model_loaded(self, model_name: str, path: str, load_time: float) -> None:
        """Log AI model loading"""
        logger = self.get_logger("models")
        logger.info(f"Loaded {model_name} from {path} in {load_time:.2f}s")
        
    def log_stream_status(self, stream_id: str, status: str, details: str = "") -> None:
        """Log stream status changes"""
        logger = self.get_logger("streams")
        message = f"Stream {stream_id}: {status}"
        if details:
            message += f" - {details}"
        logger.info(message)
        
    def log_violation_detected(self, stream_id: str, violation_type: str, confidence: float) -> None:
        """Log violation detection"""
        logger = self.get_logger("analysis")
        logger.info(f"Violation detected on {stream_id}: {violation_type} (confidence: {confidence:.2f})")
        
    def log_backend_communication(self, endpoint: str, status_code: int, duration: float) -> None:
        """Log backend API communication"""
        logger = self.get_logger("backend")
        logger.info(f"Backend API: {endpoint} -> {status_code} ({duration:.3f}s)")
        
    def set_log_level(self, component: str, level: str) -> None:
        """
        Dynamically change log level for a component.
        
        Args:
            component: Component name
            level: New log level
        """
        if component in self.loggers:
            self.loggers[component].setLevel(getattr(logging, level.upper()))
            logger = self.get_logger("config")
            logger.info(f"Changed log level for {component} to {level}")
            
    def cleanup(self) -> None:
        """Clean up logging resources"""
        for handler in self.handlers.values():
            handler.close()
        self.handlers.clear()
        self.loggers.clear()
        self.performance_loggers.clear()


# Global logging system instance
_logging_system: Optional[AIProcessorLogger] = None


def setup_logging(config: Dict[str, Any]) -> AIProcessorLogger:
    """
    Initialize the global logging system.
    
    Args:
        config: Logging configuration
        
    Returns:
        AIProcessorLogger instance
    """
    global _logging_system
    _logging_system = AIProcessorLogger(config)
    return _logging_system


def get_logger(component: str = "main") -> logging.Logger:
    """
    Get a component-specific logger.
    
    Args:
        component: Component name
        
    Returns:
        Logger instance
        
    Note:
        If logging system is not initialized, returns a basic logger
    """
    if _logging_system is None:
        # Return a basic logger if system not initialized
        basic_logger = logging.getLogger(component)
        if not basic_logger.handlers:
            # Add a basic console handler if none exists
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            basic_logger.addHandler(handler)
            basic_logger.setLevel(logging.INFO)
        return basic_logger
    return _logging_system.get_logger(component)


def get_performance_logger(component: str) -> PerformanceLogger:
    """
    Get a performance logger for a component.
    
    Args:
        component: Component name
        
    Returns:
        PerformanceLogger instance
        
    Raises:
        RuntimeError: If logging system not initialized
    """
    if _logging_system is None:
        raise RuntimeError("Logging system not initialized. Call setup_logging() first.")
    return _logging_system.get_performance_logger(component)


def log_startup(component: str, details: str = "") -> None:
    """Convenience function to log component startup"""
    if _logging_system:
        _logging_system.log_startup(component, details)


def log_shutdown(component: str, details: str = "") -> None:
    """Convenience function to log component shutdown"""
    if _logging_system:
        _logging_system.log_shutdown(component, details)


def log_error(component: str, error: Exception, context: str = "") -> None:
    """Convenience function to log errors with context"""
    if _logging_system:
        _logging_system.log_error_with_context(component, error, context)