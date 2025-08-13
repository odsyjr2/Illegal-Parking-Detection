"""
Multi-YAML Configuration Loader for AI Processor

This module provides functionality to load and merge multiple YAML configuration files
with environment variable substitution, validation, and error handling.
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors"""
    file_name: str
    section: str
    message: str
    
    def __str__(self):
        return f"Config validation error in {self.file_name}[{self.section}]: {self.message}"


@dataclass
class ConfigFile:
    """Represents a configuration file with its metadata"""
    name: str
    path: Path
    required_sections: List[str]
    optional: bool = False


class ConfigLoader:
    """
    Multi-YAML configuration loader with validation and environment variable support.
    
    Features:
    - Load and merge multiple YAML files
    - Environment variable substitution with ${VAR} syntax
    - Configuration validation with required sections
    - Error handling with detailed error messages
    - Caching for performance
    """
    
    def __init__(self, config_dir: Union[str, Path]):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._merged_config: Optional[Dict[str, Any]] = None
        
        # Define configuration files and their required sections
        self._config_files = [
            ConfigFile(
                name="config.yaml",
                path=self.config_dir / "config.yaml",
                required_sections=["application", "backend", "logging"]
            ),
            ConfigFile(
                name="models.yaml", 
                path=self.config_dir / "models.yaml",
                required_sections=["vehicle_detection", "illegal_parking", "license_plate"]
            ),
            ConfigFile(
                name="processing.yaml",
                path=self.config_dir / "processing.yaml", 
                required_sections=["monitoring", "analysis"]
            ),
            ConfigFile(
                name="streams.yaml",
                path=self.config_dir / "streams.yaml",
                required_sections=["cctv_streams"]
            )
        ]
        
    def load_all_configs(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load and merge all configuration files.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            Merged configuration dictionary
            
        Raises:
            ConfigValidationError: If validation fails
            FileNotFoundError: If required config file is missing
            yaml.YAMLError: If YAML parsing fails
        """
        if self._merged_config is not None and not force_reload:
            return self._merged_config
            
        logger.info("Loading configuration files...")
        
        merged_config = {}
        
        # Load each configuration file
        for config_file in self._config_files:
            try:
                file_config = self.load_single_config(config_file, force_reload)
                merged_config = self._merge_configs(merged_config, file_config)
                logger.debug(f"Loaded and merged {config_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to load {config_file.name}: {e}")
                raise
        
        # Substitute environment variables
        merged_config = self._substitute_env_vars(merged_config)
        
        # Validate environment variables
        self._validate_env_vars(merged_config)
        
        # Cache the merged configuration
        self._merged_config = merged_config
        
        logger.info("Configuration loading completed successfully")
        return merged_config
        
    def load_single_config(self, config_file: ConfigFile, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load a single YAML configuration file.
        
        Args:
            config_file: Configuration file information
            force_reload: Force reload even if cached
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ConfigValidationError: If validation fails
        """
        if not force_reload and config_file.name in self._cache:
            return self._cache[config_file.name]
            
        if not config_file.path.exists():
            if config_file.optional:
                logger.warning(f"Optional config file not found: {config_file.path}")
                return {}
            else:
                raise FileNotFoundError(f"Required config file not found: {config_file.path}")
        
        try:
            with open(config_file.path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file) or {}
                
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML in {config_file.name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading {config_file.name}: {e}")
            raise
            
        # Validate configuration structure
        self._validate_config(config_data, config_file)
        
        # Cache the configuration
        self._cache[config_file.name] = config_data
        
        logger.debug(f"Successfully loaded {config_file.name}")
        return config_data
        
    def _validate_config(self, config: Dict[str, Any], config_file: ConfigFile) -> None:
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary to validate
            config_file: Configuration file information
            
        Raises:
            ConfigValidationError: If validation fails
        """
        # Check for required sections
        missing_sections = []
        for section in config_file.required_sections:
            if section not in config:
                missing_sections.append(section)
                
        if missing_sections:
            raise ConfigValidationError(
                file_name=config_file.name,
                section=", ".join(missing_sections),
                message=f"Missing required sections: {missing_sections}"
            )
            
        # Perform specific validation for different config files
        if config_file.name == "models.yaml":
            self._validate_models_config(config, config_file.name)
        elif config_file.name == "processing.yaml":
            self._validate_processing_config(config, config_file.name)
        elif config_file.name == "streams.yaml":
            self._validate_streams_config(config, config_file.name)
        elif config_file.name == "config.yaml":
            self._validate_main_config(config, config_file.name)
            
    def _validate_models_config(self, config: Dict[str, Any], file_name: str) -> None:
        """Validate models.yaml specific configuration"""
        for model_name in ["vehicle_detection", "illegal_parking", "license_plate"]:
            model_config = config.get(model_name, {})
            
            if model_name == "license_plate":
                # Special validation for license plate config
                if "detector" not in model_config:
                    raise ConfigValidationError(file_name, model_name, "Missing 'detector' section")
                if "ocr" not in model_config:
                    raise ConfigValidationError(file_name, model_name, "Missing 'ocr' section")
            else:
                # Standard model validation
                if "path" not in model_config:
                    raise ConfigValidationError(file_name, model_name, "Missing 'path' parameter")
                if "confidence_threshold" not in model_config:
                    raise ConfigValidationError(file_name, model_name, "Missing 'confidence_threshold' parameter")
                    
    def _validate_processing_config(self, config: Dict[str, Any], file_name: str) -> None:
        """Validate processing.yaml specific configuration"""
        monitoring = config.get("monitoring", {})
        if "parking_duration_threshold" not in monitoring:
            raise ConfigValidationError(file_name, "monitoring", "Missing 'parking_duration_threshold' parameter")
            
        analysis = config.get("analysis", {})
        if "worker_pool_size" not in analysis:
            raise ConfigValidationError(file_name, "analysis", "Missing 'worker_pool_size' parameter")
        
        # Validate worker pool size is reasonable
        worker_pool_size = analysis.get("worker_pool_size", 0)
        if not isinstance(worker_pool_size, int) or worker_pool_size < 1 or worker_pool_size > 20:
            raise ConfigValidationError(file_name, "analysis", "worker_pool_size must be between 1 and 20")
            
    def _validate_streams_config(self, config: Dict[str, Any], file_name: str) -> None:
        """Validate streams.yaml specific configuration"""
        cctv_streams = config.get("cctv_streams", {})
        
        # Validate that at least one stream source is configured
        has_backend = cctv_streams.get("fetch_from_backend", False)
        has_local = bool(cctv_streams.get("local_streams"))
        
        if not has_backend and not has_local:
            raise ConfigValidationError(
                file_name, "cctv_streams", 
                "Must have either backend streams or local streams configured"
            )
            
    def _validate_main_config(self, config: Dict[str, Any], file_name: str) -> None:
        """Validate config.yaml specific configuration"""
        backend = config.get("backend", {})
        if "url" not in backend and "fallback_url" not in backend:
            raise ConfigValidationError(file_name, "backend", "Must have either 'url' or 'fallback_url'")
            
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively substitute environment variables in configuration.
        
        Supports ${VAR_NAME} syntax with optional default values: ${VAR_NAME:default}
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute_value(value: Any) -> Any:
            if isinstance(value, str):
                # Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
                pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
                
                def replace_env_var(match):
                    var_name = match.group(1)
                    default_value = match.group(2) if match.group(2) is not None else ""
                    
                    env_value = os.getenv(var_name)
                    if env_value is not None:
                        return env_value
                    elif default_value:
                        return default_value
                    else:
                        logger.warning(f"Environment variable {var_name} not set and no default provided")
                        return match.group(0)  # Return original if no default
                        
                return re.sub(pattern, replace_env_var, value)
                
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
                
        return substitute_value(config)
        
    def _validate_env_vars(self, config: Dict[str, Any]) -> None:
        """
        Validate that required environment variables are set.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ConfigValidationError: If required environment variables are missing
        """
        env_config = config.get("environment", {})
        required_vars = env_config.get("required_env_vars", [])
        
        missing_vars = []
        for var_name in required_vars:
            if not os.getenv(var_name):
                missing_vars.append(var_name)
                
        if missing_vars:
            raise ConfigValidationError(
                file_name="environment", 
                section="required_env_vars",
                message=f"Missing required environment variables: {missing_vars}"
            )
            
    def _merge_configs(self, base_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            new_config: Configuration to merge in
            
        Returns:
            Merged configuration dictionary
        """
        result = base_config.copy()
        
        for key, value in new_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get_config_section(self, section: str) -> Dict[str, Any]:
        """
        Get a specific configuration section.
        
        Args:
            section: Section name (e.g., "models", "processing")
            
        Returns:
            Configuration section dictionary
        """
        if self._merged_config is None:
            self.load_all_configs()
            
        return self._merged_config.get(section, {})
        
    def get_config_value(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Configuration path (e.g., "backend.url")
            default: Default value if path not found
            
        Returns:
            Configuration value
        """
        if self._merged_config is None:
            self.load_all_configs()
            
        keys = path.split('.')
        current = self._merged_config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
                
        return current
        
    def reload_config(self) -> Dict[str, Any]:
        """
        Force reload all configuration files.
        
        Returns:
            Reloaded merged configuration
        """
        logger.info("Reloading configuration files...")
        self._cache.clear()
        self._merged_config = None
        return self.load_all_configs()
        
    def validate_paths(self) -> List[str]:
        """
        Validate that all file paths in configuration exist.
        
        Returns:
            List of missing file paths
        """
        missing_paths = []
        
        if self._merged_config is None:
            self.load_all_configs()
            
        # Check model paths
        models_config = self._merged_config.get("vehicle_detection", {})
        model_path = models_config.get("path")
        if model_path:
            full_path = self.config_dir.parent / "models" / model_path
            if not full_path.exists():
                missing_paths.append(str(full_path))
                
        # Add more path validations as needed...
        
        return missing_paths


# Global configuration loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: Optional[Union[str, Path]] = None) -> ConfigLoader:
    """
    Get global configuration loader instance.
    
    Args:
        config_dir: Configuration directory (only used on first call)
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    
    if _config_loader is None:
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent.parent.parent / "config"
        _config_loader = ConfigLoader(config_dir)
        
    return _config_loader


def load_config() -> Dict[str, Any]:
    """
    Load configuration using the global configuration loader.
    
    Returns:
        Merged configuration dictionary
    """
    return get_config_loader().load_all_configs()


def get_config(section: str) -> Dict[str, Any]:
    """
    Get a specific configuration section.
    
    Args:
        section: Section name
        
    Returns:
        Configuration section dictionary
    """
    return get_config_loader().get_config_section(section)