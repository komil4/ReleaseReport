import os
import requests
import json
import base64
from typing import List, Dict, Any
from .multi_tracker_models import (
    MultiTrackerConfig, TaskTrackerConfig, TaskSearchResult, 
    MultiTaskResult, TaskDeduplicationInfo, TaskTrackerType
)
from .confluence_service import ConfluenceService

class OneCService:
    def __init__(self, config_service):
        self.config_service = config_service
        
        # Если это TaskTrackerConfig, используем его конфигурацию
        if hasattr(config_service, 'config'):
            config = config_service.config
            self.enabled = config_service.enabled
        else:
            # Если это ConfigManager, получаем 1C конфигурацию
            config = config_service.get_1c_config()
            self.enabled = True
        
        self.onec_url = config['url']
        self.username = config['username']
        self.password = config['password']
        
        if not all([self.onec_url, self.username, self.password]):
            raise ValueError('1C configuration is missing')
        
        # Инициализируем сессию для работы с 1C
        self.session = requests.Session()
        self._setup_basic_auth()
    
    def _setup_basic_auth(self):
        """Настройка Basic авторизации для 1C"""
        try:
            # Создаем строку для Basic авторизации
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            # Устанавливаем заголовок Basic авторизации
            self.session.headers.update({
                'Authorization': f"Basic {encoded_credentials}"
            })
            
            print(f'Basic auth configured for user: {self.username}')
            
        except Exception as e:
            print(f'Error setting up Basic auth for 1C: {str(e)}')
            raise
    
    def get_task_details(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Получает детали задач из 1C одним запросом"""
        try:
            # Фильтруем пустые номера задач
            valid_task_numbers = [task for task in task_numbers if task]
            
            if not valid_task_numbers:
                return []
            
            # Получаем все задачи одним запросом
            task_details = self._get_tasks_batch_from_1c(valid_task_numbers)
            
            return task_details
        except Exception as e:
            raise Exception(f'Error fetching task details from 1C: {str(e)}')
    
    def _get_tasks_batch_from_1c(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Получает информацию о нескольких задачах из 1C одним запросом"""
        try:
            # URL для получения задач пакетом
            batch_url = f"{self.onec_url}/hs/GetData/tasks"
            
            # Подготавливаем данные для POST запроса
            request_data = {
                "task_numbers": task_numbers
            }
            
            response = self.session.post(batch_url, json=request_data)
            response.raise_for_status()
            
            tasks_data = response.json()
            task_details = []
            
            # Обрабатываем полученные данные
            for task_data in tasks_data:
                if task_data:  # Проверяем, что данные задачи не пустые
                    task_info = self._process_task_data(task_data)
                    if task_info:
                        task_details.append(task_info)
            
            return task_details
            
        except Exception as e:
            print(f'Error fetching tasks batch from 1C: {str(e)}')
            # Fallback к получению задач по одной, если пакетный запрос не работает
            return self._get_tasks_individually(task_numbers)
    
    def _get_tasks_individually(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Fallback метод для получения задач по одной"""
        task_details = []
        for task_number in task_numbers:
            try:
                task_info = self._get_task_from_1c(task_number)
                if task_info:
                    task_details.append(task_info)
            except Exception as e:
                print(f'Error fetching task {task_number} from 1C: {str(e)}')
                continue
        return task_details
    
    def _process_task_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает данные задачи из 1C в стандартный формат"""
        try:
            task_number = task_data.get('task_number', '')
            if not task_number:
                return None
            
            # Преобразуем данные 1C в стандартный формат
            task_info = {
                'task_number': task_number,
                'title': task_data.get('title', ''),
                'summary': task_data.get('title', ''),
                'description': task_data.get('description', ''),
                'status': self._map_1c_status(task_data.get('status', '')),
                'priority': self._map_1c_priority(task_data.get('priority', '')),
                'assignee': task_data.get('assignee', 'Unassigned'),
                'url': task_data.get('url', '')
                #'confluence_pages': self._get_confluence_attachments(task_number, task_data)
            }
            
            return task_info
            
        except Exception as e:
            print(f'Error processing task data: {str(e)}')
            return None
    
    def _get_task_from_1c(self, task_number: str) -> Dict[str, Any]:
        """Получает информацию о задаче из 1C (для fallback)"""
        try:
            # URL для получения задачи по номеру
            task_url = f"{self.onec_url}/hs/api/tasks/{task_number}"
            
            response = self.session.get(task_url)
            response.raise_for_status()
            
            task_data = response.json()
            
            # Используем общий метод обработки данных
            return self._process_task_data(task_data)
            
        except Exception as e:
            print(f'Error fetching task {task_number} from 1C: {str(e)}')
            return None
    
    def _map_1c_status(self, status: str) -> str:
        """Преобразует статус из 1C в стандартный формат"""
        status_mapping = {
            'Новая': 'New',
            'В работе': 'In Progress',
            'Выполнена': 'Done',
            'Закрыта': 'Closed',
            'Отменена': 'Cancelled',
            'Приостановлена': 'On Hold'
        }
        return status_mapping.get(status, status)
    
    def _map_1c_priority(self, priority: str) -> str:
        """Преобразует приоритет из 1C в стандартный формат"""
        priority_mapping = {
            'Низкий': 'Low',
            'Средний': 'Medium',
            'Высокий': 'High',
            'Критический': 'Critical'
        }
        return priority_mapping.get(priority, priority)
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервис 1C"""
        return self.enabled