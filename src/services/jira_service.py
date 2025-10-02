import os
import requests
import json
import base64
from jira import JIRA
from typing import List, Dict, Any
from .multi_tracker_models import (
    MultiTrackerConfig, TaskTrackerConfig, TaskSearchResult, 
    MultiTaskResult, TaskDeduplicationInfo, TaskTrackerType
)

class JiraService:
    def __init__(self, config_service):
        self.config_service = config_service
        
        # Если это TaskTrackerConfig, используем его конфигурацию
        if hasattr(config_service, 'config'):
            config = config_service.config
            self.enabled = config_service.enabled
        else:
            # Если это ConfigManager, получаем Jira конфигурацию
            config = config_service.get_jira_config()
            self.enabled = True
        
        self.jira_url = config['url']
        self.jira_email = config['email']
        self.jira_token = config['api_token']
        
        if not all([self.jira_url, self.jira_email, self.jira_token]):
            raise ValueError('Jira configuration is missing')
        
        self.jira = JIRA(
            server=self.jira_url,
            token_auth=self.jira_token
        )
    
    def get_task_details(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Получает детали задач из Jira одним запросом"""
        try:
            # Фильтруем пустые номера задач
            valid_task_numbers = [task for task in task_numbers if task]
            
            if not valid_task_numbers:
                return []
            
            # Получаем все задачи одним запросом
            task_details = self._get_tasks_batch_from_jira(valid_task_numbers)
            
            return task_details
        except Exception as e:
            raise Exception(f'Error fetching task details from Jira: {str(e)}')
    
    def _get_tasks_batch_from_jira(self, task_numbers: List[str]) -> List[Dict[str, Any]]:
        """Получает информацию о нескольких задачах из Jira одним запросом"""
        try:
            task_details = []
            for task_number in task_numbers:
                try:
                    issue = self.jira.issue(task_number)
                    task_info = self._process_task_data(issue, task_number)
                    if task_info:
                        task_details.append(task_info)
                except Exception as e:
                    print(f'Error fetching task {task_number} from Jira: {str(e)}')
                    continue
            
            return task_details
            
        except Exception as e:
            print(f'Error fetching tasks batch from Jira: {str(e)}')
            return []
    
    def _process_task_data(self, issue, task_number: str) -> Dict[str, Any]:
        """Обрабатывает данные задачи из Jira в стандартный формат"""
        try:
            if not task_number:
                return None
            
            # Преобразуем данные Jira в стандартный формат
            task_info = {
                'task_number': task_number,
                'title': issue.fields.summary,
                'summary': issue.fields.summary,
                'description': issue.fields.description or '',
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else 'Medium',
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'url': f'{self.jira_url}/browse/{task_number}',
                'confluence_pages': []  # Будет заполнено позже отдельным сервисом
            }
            
            return task_info
            
        except Exception as e:
            print(f'Error processing task data: {str(e)}')
            return None
    
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервис Jira"""
        return self.enabled
