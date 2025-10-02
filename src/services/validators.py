"""
Валидаторы для системы отчетов
"""
from typing import List, Dict, Any, Optional
from .base import ValidationError, CommitData, TaskData, MetadataChanges
from .constants import MESSAGES


class DataValidator:
    """Валидатор данных для отчетов"""
    
    @staticmethod
    def validate_commit_data(commits: List[Dict[str, Any]]) -> List[CommitData]:
        """Валидирует и преобразует данные коммитов"""
        if not isinstance(commits, list):
            raise ValidationError("Commits must be a list")
        
        validated_commits = []
        for i, commit in enumerate(commits):
            try:
                validated_commit = CommitData(
                    id=DataValidator._validate_string(commit.get('id'), f"commit[{i}].id"),
                    message=DataValidator._validate_string(commit.get('message'), f"commit[{i}].message"),
                    author=DataValidator._validate_string(commit.get('author', commit.get('author_name')), f"commit[{i}].author"),
                    date=DataValidator._validate_string(commit.get('date'), f"commit[{i}].date"),
                    task_number=commit.get('task_number'),
                    total_lines=DataValidator._validate_int(commit.get('total', 0), f"commit[{i}].total"),
                    url=commit.get('url')
                )
                validated_commits.append(validated_commit)
            except Exception as e:
                raise ValidationError(f"Invalid commit data at index {i}: {str(e)}")
        
        return validated_commits
    
    @staticmethod
    def validate_task_data(tasks: List[Dict[str, Any]]) -> List[TaskData]:
        """Валидирует и преобразует данные задач"""
        if not isinstance(tasks, list):
            raise ValidationError("Tasks must be a list")
        
        validated_tasks = []
        for i, task in enumerate(tasks):
            try:
                validated_task = TaskData(
                    task_number=DataValidator._validate_string(task.get('task_number'), f"task[{i}].task_number"),
                    summary=DataValidator._validate_string(task.get('summary'), f"task[{i}].summary"),
                    description=task.get('description', ''),
                    status=DataValidator._validate_string(task.get('status'), f"task[{i}].status"),
                    priority=DataValidator._validate_string(task.get('priority'), f"task[{i}].priority"),
                    url=DataValidator._validate_string(task.get('url'), f"task[{i}].url"),
                    confluence_pages=task.get('confluence_pages', [])
                )
                validated_tasks.append(validated_task)
            except Exception as e:
                raise ValidationError(f"Invalid task data at index {i}: {str(e)}")
        
        return validated_tasks
    
    @staticmethod
    def validate_metadata_changes(metadata: Dict[str, Any]) -> Optional[MetadataChanges]:
        """Валидирует данные изменений метаданных"""
        if not metadata:
            return None
        
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata changes must be a dictionary")
        
        try:
            return MetadataChanges(
                has_changes=DataValidator._validate_bool(metadata.get('has_changes', False), "metadata.has_changes"),
                since_commit_date=metadata.get('since_commit_date'),
                current_commit_date=metadata.get('current_commit_date'),
                added_metadata=metadata.get('added_metadata', []),
                removed_metadata=metadata.get('removed_metadata', []),
                modified_metadata=metadata.get('modified_metadata', []),
                summary=metadata.get('summary', {})
            )
        except Exception as e:
            raise ValidationError(f"Invalid metadata changes: {str(e)}")
    
    @staticmethod
    def _validate_string(value: Any, field_name: str) -> str:
        """Валидирует строковое значение"""
        if value is None:
            raise ValidationError(f"{field_name} is required")
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        return value
    
    @staticmethod
    def _validate_int(value: Any, field_name: str) -> int:
        """Валидирует целочисленное значение"""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be an integer")
    
    @staticmethod
    def _validate_bool(value: Any, field_name: str) -> bool:
        """Валидирует булево значение"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)


class ConfigValidator:
    """Валидатор конфигурации"""
    
    @staticmethod
    def validate_confluence_config(config: Dict[str, Any]) -> None:
        """Валидирует конфигурацию Confluence"""
        required_fields = ['url', 'email', 'api_token', 'space_key']
        for field in required_fields:
            if not config.get(field):
                raise ValidationError(f"Confluence configuration missing required field: {field}")
    
    @staticmethod
    def validate_gitlab_config(config: Dict[str, Any]) -> None:
        """Валидирует конфигурацию GitLab"""
        required_fields = ['url', 'group', 'project']
        for field in required_fields:
            if not config.get(field):
                raise ValidationError(f"GitLab configuration missing required field: {field}")
    
    @staticmethod
    def validate_jira_config(config: Dict[str, Any]) -> None:
        """Валидирует конфигурацию Jira"""
        required_fields = ['url']
        for field in required_fields:
            if not config.get(field):
                raise ValidationError(f"Jira configuration missing required field: {field}")
