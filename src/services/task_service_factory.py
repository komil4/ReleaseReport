from typing import Union
from .multi_tracker_models import (
    MultiTrackerConfig, TaskTrackerConfig, TaskSearchResult, 
    MultiTaskResult, TaskDeduplicationInfo, TaskTrackerType
)
from .jira_service import JiraService
from .onec_service import OneCService

class TaskServiceFactory:
    """Фабрика для создания сервисов таск-трекеров"""
    
    @staticmethod
    def create_task_service(config_service: TaskTrackerConfig) -> Union[JiraService, OneCService]:
        """
        Создает сервис таск-трекера на основе конфигурации
        
        Args:
            config_service: Сервис конфигурации
            
        Returns:
            Сервис таск-трекера (JiraService или OneCService)
            
        Raises:
            ValueError: Если тип таск-трекера не поддерживается
        """
        if not config_service.enabled:
            raise ValueError("Task tracker is disabled in configuration")
        
        task_tracker_type = config_service.type.value
        
        if task_tracker_type == 'jira':
            return JiraService(config_service)
        elif task_tracker_type == 'onec':
            return OneCService(config_service)
        else:
            raise ValueError(f"Unsupported task tracker type: {task_tracker_type}")
    
    @staticmethod
    def get_available_task_trackers() -> list:
        """
        Возвращает список доступных типов таск-трекеров
        
        Returns:
            Список строк с типами таск-трекеров
        """
        return ['jira', '1c']
    
    @staticmethod
    def is_task_tracker_available(config_service: TaskTrackerConfig, task_tracker_type: str) -> bool:
        """
        Проверяет, доступен ли указанный тип таск-трекера
        
        Args:
            config_service: Сервис конфигурации
            task_tracker_type: Тип таск-трекера для проверки
            
        Returns:
            True если таск-трекер доступен, False в противном случае
        """
        if task_tracker_type == 'jira':
            try:
                jira_config = config_service.get_jira_config()
                return all([jira_config.get('url'), jira_config.get('email'), jira_config.get('api_token')])
            except:
                return False
        elif task_tracker_type == 'onec':
            try:
                onec_config = config_service.get_1c_config()
                return all([onec_config.get('url'), onec_config.get('username'), 
                           onec_config.get('password'), onec_config.get('database')])
            except:
                return False
        else:
            return False
