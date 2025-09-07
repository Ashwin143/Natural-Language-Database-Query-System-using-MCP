"""Configuration manager for the NLDB query system."""

import os
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


class ConfigManager:
    """Configuration manager for system settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment and files."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Default configuration
        self.config = {
            "databases": {
                "primary": {
                    "url": os.getenv("PRIMARY_DB_URL"),
                    "driver": "postgresql",
                    "pool_size": int(os.getenv("PRIMARY_DB_POOL_SIZE", "10")),
                    "timeout": int(os.getenv("PRIMARY_DB_TIMEOUT", "30"))
                },
                "analytics": {
                    "url": os.getenv("ANALYTICS_DB_URL"),
                    "driver": "postgresql", 
                    "pool_size": int(os.getenv("ANALYTICS_DB_POOL_SIZE", "10")),
                    "timeout": int(os.getenv("ANALYTICS_DB_TIMEOUT", "30"))
                }
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            },
            "mcp": {
                "host": os.getenv("MCP_SERVER_HOST", "localhost"),
                "port": int(os.getenv("MCP_SERVER_PORT", "8000"))
            },
            "query": {
                "timeout": int(os.getenv("MAX_QUERY_TIMEOUT", "30")),
                "max_results": int(os.getenv("MAX_RESULT_ROWS", "1000"))
            },
            "security": {
                "secret_key": os.getenv("SECRET_KEY"),
                "allowed_hosts": os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO")
            }
        }
        
        # Load additional configuration from file if provided
        if self.config_path and os.path.exists(self.config_path):
            try:
                import json
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    self._merge_config(file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config file {self.config_path}: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration with existing configuration."""
        def merge_dicts(base_dict, new_dict):
            for key, value in new_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    merge_dicts(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        merge_dicts(self.config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation like 'database.primary.url')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config_dict = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config_dict:
                config_dict[k] = {}
            config_dict = config_dict[k]
        
        # Set the value
        config_dict[keys[-1]] = value
    
    def get_database_config(self, database_name: str) -> Optional[Dict[str, Any]]:
        """Get database configuration by name.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Database configuration or None
        """
        return self.get(f"databases.{database_name}")
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration."""
        return self.get("openai", {})
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP server configuration."""
        return self.get("mcp", {})
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        # Check required fields
        required_fields = [
            "openai.api_key"
        ]
        
        for field in required_fields:
            if not self.get(field):
                logger.error(f"Missing required configuration: {field}")
                return False
        
        # Check database connections
        primary_db = self.get("databases.primary.url")
        analytics_db = self.get("databases.analytics.url")
        
        if not primary_db and not analytics_db:
            logger.error("At least one database connection must be configured")
            return False
        
        return True
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration (excluding sensitive data)."""
        safe_config = {}
        
        for key, value in self.config.items():
            if key == "security":
                # Exclude sensitive security data
                safe_config[key] = {"allowed_hosts": value.get("allowed_hosts", [])}
            elif key == "openai":
                # Mask API key
                safe_config[key] = {
                    "model": value.get("model"),
                    "temperature": value.get("temperature"),
                    "api_key": "***" if value.get("api_key") else None
                }
            elif key == "databases":
                # Mask database URLs
                safe_databases = {}
                for db_name, db_config in value.items():
                    if db_config and db_config.get("url"):
                        safe_databases[db_name] = {
                            **db_config,
                            "url": self._mask_database_url(db_config["url"])
                        }
                safe_config[key] = safe_databases
            else:
                safe_config[key] = value
        
        return safe_config
    
    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive parts of database URL."""
        if not url:
            return url
        
        # Replace password with asterisks
        import re
        pattern = r'://([^:]+):([^@]+)@'
        replacement = r'://\1:***@'
        return re.sub(pattern, replacement, url)
    
    def validate_database_connections(self) -> Dict[str, bool]:
        """Validate database connection configurations.
        
        Returns:
            Dictionary with database names and their validity
        """
        validation_results = {}
        
        for db_name in ["primary", "analytics"]:
            db_config = self.get_database_config(db_name)
            if db_config and db_config.get("url"):
                validation_results[db_name] = True
            else:
                validation_results[db_name] = False
        
        return validation_results
