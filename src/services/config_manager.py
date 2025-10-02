"""
Менеджер конфигурации для работы с множественными файлами
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from .base import BaseService, ConfigurationError
from .validators import ConfigValidator
from .logger_config import get_logger
from .multi_tracker_models import MultiTrackerConfig, TaskTrackerConfig, TaskTrackerType


class ConfigManager(BaseService):
    """Менеджер конфигурации для работы с множественными файлами"""
    
    def __init__(self, config_dir: str = "config"):
        super().__init__(None)
        self.config_dir = Path(config_dir)
        self.logger = get_logger(self.__class__.__name__)
        self._config_cache = {}
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Загружает все конфигурационные файлы"""
        try:
            # Проверяем существование директории конфигурации
            if not self.config_dir.exists():
                self.logger.warning(f"Config directory {self.config_dir} does not exist, creating...")
                self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Загружаем основные конфигурации
            self._load_config_file('app.json')
            self._load_config_file('gitlab.json')
            self._load_config_file('confluence.json')
            self._load_config_file('trackers.json')
            
            # Валидируем конфигурации
            self._validate_all_configs()
            
            self.logger.info("All configuration files loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration files: {str(e)}")
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def _load_config_file(self, filename: str) -> None:
        """Загружает отдельный конфигурационный файл"""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            self.logger.warning(f"Config file {filename} not found, skipping...")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Извлекаем ключ конфигурации (первый ключ в JSON)
            config_key = list(config_data.keys())[0]
            self._config_cache[config_key] = config_data[config_key]
            
            self.logger.debug(f"Loaded config section '{config_key}' from {filename}")
            
        except Exception as e:
            self.logger.error(f"Error loading config file {filename}: {str(e)}")
            raise ConfigurationError(f"Failed to load {filename}: {str(e)}")
    
    def _validate_all_configs(self) -> None:
        """Валидирует все загруженные конфигурации"""
        try:
            # Валидируем GitLab конфигурацию
            if 'gitlab' in self._config_cache:
                ConfigValidator.validate_gitlab_config(self._config_cache['gitlab'])
            
            # Валидируем Confluence конфигурацию
            if 'confluence' in self._config_cache:
                ConfigValidator.validate_confluence_config(self._config_cache['confluence'])
            
            # Валидируем конфигурацию трекеров
            if 'trackers' in self._config_cache:
                self._validate_trackers_config()
            
            self.logger.info("All configurations validated successfully")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")
    
    def _validate_trackers_config(self) -> None:
        """Валидирует конфигурацию трекеров"""
        trackers_config = self._config_cache['trackers']
        
        if not trackers_config.get('enabled', True):
            return
        
        trackers = trackers_config.get('trackers', [])
        if not trackers:
            raise ConfigurationError("No trackers configured")
        
        for i, tracker_data in enumerate(trackers):
            if not tracker_data.get('name'):
                raise ConfigurationError(f"Tracker {i} missing name")
            
            if not tracker_data.get('type'):
                raise ConfigurationError(f"Tracker {i} missing type")
            
            try:
                TaskTrackerType(tracker_data['type'])
            except ValueError:
                raise ConfigurationError(f"Tracker {i} has invalid type: {tracker_data['type']}")
    
    def get_app_config(self) -> Dict[str, Any]:
        """Получает конфигурацию приложения"""
        return self._config_cache.get('app', {})
    
    def get_gitlab_config(self) -> Dict[str, str]:
        """Получает конфигурацию GitLab"""
        if 'gitlab' not in self._config_cache:
            raise ConfigurationError("GitLab configuration not found")
        return self._config_cache['gitlab']
    
    def get_confluence_config(self) -> Dict[str, str]:
        """Получает конфигурацию Confluence"""
        if 'confluence' not in self._config_cache:
            raise ConfigurationError("Confluence configuration not found")
        return self._config_cache['confluence']
    
    def get_multi_tracker_config(self) -> MultiTrackerConfig:
        """Получает конфигурацию множественных таск-трекеров"""
        if 'trackers' not in self._config_cache:
            # Возвращаем конфигурацию на основе legacy настроек
            raise ConfigurationError("Task trackers configuration not found")
        
        trackers_config = self._config_cache['trackers']
        
        if not trackers_config.get('enabled', True):
            return MultiTrackerConfig(trackers=[], deduplication_enabled=False)
        
        trackers = []
        for tracker_data in trackers_config.get('trackers', []):
            if not tracker_data.get('enabled', True):
                continue
            
            tracker_config = TaskTrackerConfig(
                name=tracker_data['name'],
                type=TaskTrackerType(tracker_data['type']),
                enabled=tracker_data.get('enabled', True),
                config=tracker_data.get('config', {}),
                priority=tracker_data.get('priority', 0),
                description=tracker_data.get('description')
            )
            trackers.append(tracker_config)
        
        return MultiTrackerConfig(
            trackers=trackers,
            deduplication_enabled=trackers_config.get('deduplication_enabled', True),
            merge_strategy=trackers_config.get('merge_strategy', 'priority'),
            timeout_seconds=trackers_config.get('timeout_seconds', 30)
        )
    
    def get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """Получает значение конфигурации по секции и ключу"""
        try:
            return self._config_cache[section][key]
        except KeyError:
            if default is not None:
                return default
            raise ConfigurationError(f"Configuration key '{section}.{key}' not found")
    
    def get_all_config(self) -> Dict[str, Any]:
        """Получает всю конфигурацию"""
        return self._config_cache.copy()
    
    def reload_config(self) -> None:
        """Перезагружает конфигурацию"""
        self.logger.info("Reloading configuration...")
        self._config_cache.clear()
        self._load_all_configs()
        self.logger.info("Configuration reloaded successfully")
    
    def get_config_file_path(self, filename: str) -> Path:
        """Получает путь к конфигурационному файлу"""
        return self.config_dir / filename
    
    def create_config_file(self, filename: str, config_data: Dict[str, Any]) -> None:
        """Создает новый конфигурационный файл"""
        config_path = self.config_dir / filename
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Created config file: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error creating config file {filename}: {str(e)}")
            raise ConfigurationError(f"Failed to create {filename}: {str(e)}")
    
    def backup_config(self, backup_dir: str = "config/backup") -> None:
        """Создает резервную копию конфигурации"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            for config_file in self.config_dir.glob("*.json"):
                backup_file = backup_path / f"{config_file.stem}_{timestamp}.json"
                shutil.copy2(config_file, backup_file)
            
            self.logger.info(f"Configuration backed up to {backup_dir}")
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            raise ConfigurationError(f"Failed to create backup: {str(e)}")
    
    def get_task_tracker_config(self) -> Dict[str, Any]:
        """Получает конфигурацию таск-трекера (для обратной совместимости)"""
        trackers_config = self._config_cache.get('trackers', {})
        legacy_config = trackers_config.get('legacy', {})
        return legacy_config.get('task_tracker', {'type': 'jira', 'enabled': False})
    
    def get_1c_config(self) -> Dict[str, str]:
        """Получает конфигурацию 1C"""
        trackers_config = self._config_cache.get('trackers', {})
        legacy_config = trackers_config.get('legacy', {})
        return legacy_config.get('1c', {})
    
    def get_jira_config(self) -> Dict[str, str]:
        """Получает конфигурацию Jira"""
        trackers_config = self._config_cache.get('trackers', {})
        legacy_config = trackers_config.get('legacy', {})
        return legacy_config.get('jira', {})