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
            
            # Извлекаем значение customfield_10604 (задача интрасервис)
            intraservice_task = None
            intraservice_task_url = None
            if hasattr(issue.fields, 'customfield_10604') and issue.fields.customfield_10604:
                intraservice_task = str(issue.fields.customfield_10604)
                intraservice_task_url = f'https://helpdesk.iek.local/Task/View/{intraservice_task}'
            
            # Извлекаем приоритет задачи
            priority_name = 'Средний'  # Значение по умолчанию
            if hasattr(issue.fields, 'priority') and issue.fields.priority:
                if hasattr(issue.fields.priority, 'name'):
                    priority_name = issue.fields.priority.name
                elif hasattr(issue.fields.priority, 'value'):
                    priority_name = issue.fields.priority.value
                else:
                    priority_name = str(issue.fields.priority)
            
            # Преобразуем данные Jira в стандартный формат
            task_info = {
                'task_number': task_number,
                'title': issue.fields.summary,
                'summary': issue.fields.summary,
                'description': issue.fields.description or '',
                'status': issue.fields.status.name,
                'priority': priority_name,
                'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
                'url': f'{self.jira_url}/browse/{task_number}',
                'intraservice_task': intraservice_task,
                'intraservice_task_url': intraservice_task_url,
                'confluence_pages': []  # Будет заполнено позже отдельным сервисом
            }
            
            return task_info
            
        except Exception as e:
            print(f'Error processing task data: {str(e)}')
            return None
    
    
    def is_enabled(self) -> bool:
        """Проверяет, включен ли сервис Jira"""
        return self.enabled
    
    def create_release(self, release_number: int, report_url: str, ready_tasks: List[str]) -> Dict[str, Any]:
        """Создает релиз в Jira с указанным номером, ссылкой на отчет и списком готовых задач"""
        try:
            # Формируем название релиза
            release_name = f"Release {release_number}"
            
            # Формируем описание релиза
            description = f"Отчет о релизе: {report_url}\n\n"
            if ready_tasks:
                description += "Задачи в релизе:\n"
                for task in ready_tasks:
                    description += f"- {task}\n"
            else:
                description += "В релизе нет задач со статусом 'Готово'"
            
            # Создаем релиз в Jira
            release_data = {
                'name': release_name,
                'description': description,
                'project': self._get_project_key(),
                'released': True,
                'releaseDate': self._get_current_date()
            }
            
            # Здесь должен быть код создания релиза через Jira API
            # Пока что возвращаем заглушку
            return {
                'success': True,
                'release_name': release_name,
                'release_number': release_number,
                'message': f'Релиз {release_name} успешно создан'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Ошибка при создании релиза: {str(e)}'
            }
    
    def get_last_release_number(self) -> int:
        """Получает номер последнего созданного релиза"""
        try:
            # Здесь должен быть код получения последнего релиза через Jira API
            # Пока что возвращаем заглушку
            return 1
            
        except Exception as e:
            print(f'Error getting last release number: {str(e)}')
            return 1
    
    def _get_project_key(self) -> str:
        """Получает ключ проекта из конфигурации"""
        # Если это TaskTrackerConfig, используем его конфигурацию
        if hasattr(self.config_service, 'config'):
            config = self.config_service.config
        else:
            # Если это ConfigManager, получаем Jira конфигурацию
            config = self.config_service.get_jira_config()
        
        return config.get('project_key', 'PROJ')
    
    def _get_current_date(self) -> str:
        """Возвращает текущую дату в формате ISO"""
        from datetime import datetime
        return datetime.now().isoformat()
