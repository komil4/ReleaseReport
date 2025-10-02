"""
Менеджер данных для системы отчетов
"""
from typing import List, Dict, Any, Optional
import logging
from .base import BaseService, CommitData, TaskData, MetadataChanges, ServiceError
from .validators import DataValidator
from .gitlab_service import GitLabService
from .metadata_service import MetadataService
from .task_service_factory import TaskServiceFactory
from .multi_tracker_service import MultiTrackerService
from .confluence_data_service import ConfluenceDataService
from .constants import FILE_PATHS, MESSAGES


class DataManager(BaseService):
    """Менеджер данных для отчетов"""
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.config_manager = config_manager
        self.gitlab_service = GitLabService(config_manager)
        self.metadata_service = MetadataService(config_manager)
        
        # Получаем путь к файлу коммитов из конфигурации приложения
        app_config = config_manager.get_app_config()
        self.commits_file = app_config.get('commits_file', FILE_PATHS['commits_file'])
        
        # Инициализируем сервис таск-трекеров
        self.task_service = None
        self.multi_task_service = None
        
        try:
            self.multi_task_service = MultiTrackerService(config_manager)
            self.logger.info(f"Initialized multi-task service with {len(self.multi_task_service.tracker_services)} trackers")
                
        except Exception as e:
            self.logger.warning(f"Could not initialize task service: {str(e)}")
            self.task_service = None
            self.multi_task_service = None
        
        # Инициализируем сервис данных Confluence
        self.confluence_data_service = ConfluenceDataService(config_manager)
    
    def get_report_data(self, last_commit: Optional[str] = None) -> Dict[str, Any]:
        """Получает все данные для отчета"""
        try:
            # Получаем коммиты
            commits_data = self._get_commits_data(last_commit)
            if not commits_data:
                return {
                    'commits': [],
                    'tasks': [],
                    'metadata': None,
                    'has_data': False,
                    'message': MESSAGES['no_commits']
                }
            
            # Получаем задачи
            tasks_data = self._get_tasks_data(commits_data)
            
            # Получаем метаданные
            metadata_data = self._get_metadata_data(commits_data)
            
            return {
                'commits': commits_data,
                'tasks': tasks_data,
                'metadata': metadata_data,
                'has_data': True,
                'message': 'Data retrieved successfully'
            }
            
        except Exception as e:
            self._handle_error(e, "getting report data")
    
    def get_report_data_with_date_filter(self, last_commit: Optional[str] = None, report_date = None) -> Dict[str, Any]:
        """Получает все данные для отчета с фильтрацией по дате формирования"""
        try:
            # Получаем коммиты
            commits_data = self._get_commits_data_with_date_filter(last_commit, report_date)
            if not commits_data:
                return {
                    'commits': [],
                    'tasks': [],
                    'metadata': None,
                    'has_data': False,
                    'message': MESSAGES['no_commits']
                }
            
            # Получаем задачи
            tasks_data = self._get_tasks_data(commits_data)
            
            # Получаем метаданные
            metadata_data = self._get_metadata_data(commits_data)
            
            return {
                'commits': commits_data,
                'tasks': tasks_data,
                'metadata': metadata_data,
                'has_data': True,
                'message': 'Data retrieved successfully'
            }
            
        except Exception as e:
            self._handle_error(e, "getting report data with date filter")
    
    def _get_commits_data(self, last_commit: Optional[str] = None) -> List[CommitData]:
        """Получает данные коммитов"""
        try:
            commits = self.gitlab_service.get_commits_since(last_commit)
            if not commits:
                return []
            
            return DataValidator.validate_commit_data(commits)
            
        except Exception as e:
            self.logger.error(f"Error getting commits data: {str(e)}")
            raise ServiceError(f"Failed to get commits data: {str(e)}")
    
    def _get_commits_data_with_date_filter(self, last_commit: Optional[str] = None, report_date = None) -> List[CommitData]:
        """Получает данные коммитов с фильтрацией по дате формирования"""
        try:
            from datetime import datetime
            
            # Получаем все коммиты с даты last_commit
            commits = self.gitlab_service.get_commits_since(last_commit)
            if not commits:
                return []
            
            # Если указана дата формирования отчета, фильтруем коммиты
            if report_date:
                filtered_commits = []
                for commit in commits:
                    try:
                        # Парсим дату коммита
                        commit_date = datetime.fromisoformat(commit['date'].replace('Z', '+00:00'))
                        
                        # Оставляем только коммиты до указанной даты формирования
                        if commit_date <= report_date:
                            filtered_commits.append(commit)
                    except Exception as e:
                        self.logger.warning(f"Could not parse commit date: {commit.get('date')}, error: {str(e)}")
                        # Если не можем распарсить дату, включаем коммит
                        filtered_commits.append(commit)
                
                commits = filtered_commits
            
            return DataValidator.validate_commit_data(commits)
            
        except Exception as e:
            self.logger.error(f"Error getting commits data with date filter: {str(e)}")
            raise ServiceError(f"Failed to get commits data with date filter: {str(e)}")
    
    def _get_tasks_data(self, commits: List[CommitData]) -> List[TaskData]:
        """Получает данные задач"""
        try:
            # Извлекаем номера задач из коммитов
            task_numbers = list(set([
                commit.task_number for commit in commits 
                if commit.task_number
            ]))
            
            if not task_numbers:
                return []
            
            # Выбираем сервис для получения задач
            if self.multi_task_service:
                # Используем множественные трекеры
                task_details = self.multi_task_service.get_task_details(task_numbers)
                self.logger.info(f"Found {len(task_details)} tasks using multi-tracker service")
            elif self.task_service:
                # Используем одиночный трекер
                task_details = self.task_service.get_task_details(task_numbers)
                self.logger.info(f"Found {len(task_details)} tasks using single tracker service")
            else:
                self.logger.warning(MESSAGES['warning_no_task_service'])
                return []
            
            if not task_details:
                return []
            
            # Обогащаем задачи данными Confluence
            enriched_task_details = self.confluence_data_service.enrich_tasks_with_confluence_data(
                task_details, 
                self._get_jira_service_for_confluence()
            )
            
            return DataValidator.validate_task_data(enriched_task_details)
            
        except Exception as e:
            self.logger.error(f"Error getting tasks data: {str(e)}")
            raise ServiceError(f"Failed to get tasks data: {str(e)}")
    
    def _get_metadata_data(self, commits: List[CommitData]) -> Optional[MetadataChanges]:
        """Получает данные метаданных"""
        try:
            # Получаем дату последнего коммита для анализа метаданных
            last_commit_date = None
            if commits:
                last_commit_date = commits[0].date
            
            self.logger.info(f"Analyzing metadata changes since: {last_commit_date}")
            metadata_changes = self.metadata_service.analyze_metadata_changes(last_commit_date)
            
            if not metadata_changes:
                self.logger.info("No metadata changes data returned")
                return None
                
            if not metadata_changes.get('has_changes', False):
                self.logger.info(f"Metadata analysis result: {metadata_changes.get('message', 'No changes')}")
                return None
            
            self.logger.info(f"Metadata changes found: {metadata_changes.get('summary', {})}")
            return DataValidator.validate_metadata_changes(metadata_changes)
            
        except Exception as e:
            self.logger.warning(f"{MESSAGES['warning_metadata_analysis']}: {str(e)}")
            return None
    
    def get_last_commit(self) -> Optional[str]:
        """Получает последний обработанный коммит"""
        try:
            if not self._file_exists(self.commits_file):
                return None
            
            with open(self.commits_file, 'r', encoding='utf-8') as f:
                commit = f.read().strip()
                return commit if commit else None
                
        except Exception as e:
            self.logger.error(f"Error reading last commit: {str(e)}")
            return None
    
    def save_last_commit(self, commit_hash: str) -> None:
        """Сохраняет последний обработанный коммит"""
        try:
            with open(self.commits_file, 'w', encoding='utf-8') as f:
                f.write(commit_hash)
                
        except Exception as e:
            self.logger.error(f"Error saving last commit: {str(e)}")
            raise ServiceError(f"Failed to save last commit: {str(e)}")
    
    def get_latest_commit(self) -> Optional[str]:
        """Получает хеш последнего коммита"""
        try:
            latest_commit = self.gitlab_service.get_latest_commit()
            return latest_commit.get('id') if latest_commit else None
            
        except Exception as e:
            self.logger.error(f"Error getting latest commit: {str(e)}")
            return None
    
    def _file_exists(self, file_path: str) -> bool:
        """Проверяет существование файла"""
        import os
        return os.path.exists(file_path)
    
    def get_task_tracker_info(self) -> Dict[str, Any]:
        """Возвращает информацию о таск-трекерах"""
        if self.multi_task_service:
            # Возвращаем информацию о множественных трекерах
            return self.multi_task_service.get_task_trackers_info()
        else:
            return {
                'type': 'none',
                'enabled': False,
                'message': 'No task tracker configured'
            }
    
    def _get_jira_service_for_confluence(self):
        """Получает JiraService для обогащения данными Confluence"""
        if not self.multi_task_service:
            return None
        
        # Ищем JiraService среди трекеров
        for tracker_name, tracker_info in self.multi_task_service.tracker_services.items():
            if tracker_info['type'].value == 'jira':
                return tracker_info['service']
        
        return None
