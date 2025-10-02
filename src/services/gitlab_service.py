import gitlab
import os
from typing import List, Dict, Any
import re
from .config_manager import ConfigManager

class GitLabService:
    def __init__(self, config_service: ConfigManager):
        self.config_service = config_service
        gitlab_config = self.config_service.get_gitlab_config()
        
        self.gitlab_url = gitlab_config['url']
        self.gitlab_token = gitlab_config['token']
        self.project_id = gitlab_config['project_id']
        
        if not all([self.gitlab_url, self.gitlab_token, self.project_id]):
            raise ValueError('GitLab configuration is missing')
        
        self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.gitlab_token, ssl_verify=False)
        self.project = self.gl.projects.get(self.project_id)
    
    def get_commits_since(self, since_commit: str = None) -> List[Dict[str, Any]]:
        try:
            commits = self.project.commits.list(all=True, since=since_commit)
            commit_data = []
            for commit in commits:
                commit_detail = self.project.commits.get(commit.id)
                stats = commit_detail.stats
                task_number = self._extract_task_number(commit.message)
                
                # Формируем URL коммита
                commit_url = f'{self.gitlab_url}/{self.project.path_with_namespace}/-/commit/{commit.id}'
                
                commit_info = {
                    'id': commit.id,
                    'author': commit.author_name,
                    'message': commit.message,
                    'date': commit.created_at,
                    'task_number': task_number,
                    'additions': stats.get('additions', 0),
                    'deletions': stats.get('deletions', 0),
                    'total': stats.get('total', 0),
                    'url': commit_url
                }
                commit_data.append(commit_info)
            return commit_data
        except Exception as e:
            raise Exception(f'Error fetching commits: {str(e)}')
    
    def _extract_task_number(self, message: str) -> str:
        patterns = [r'^([A-Z]+-\d+)', r'^#(\d+)', r'^(\d+)']
        for pattern in patterns:
            match = re.search(pattern, message.strip())
            if match:
                return match.group(1)
        return None
    
    def get_latest_commit(self) -> str:
        try:
            commits = self.project.commits.list(per_page=1)
            if commits:
                return commits[0].created_at
            return None
        except Exception as e:
            raise Exception(f'Error fetching latest commit: {str(e)}')
    
    def get_file_changes_since(self, file_path: str, since_commit_date: str = None) -> Dict[str, Any]:
        """
        Получает информацию об изменениях файла с определенной даты
        
        Args:
            file_path: путь к файлу в репозитории
            since_commit_date: дата коммита для начала отслеживания изменений
        
        Returns:
            Словарь с информацией об изменениях файла
        """
        try:
            # Получаем коммиты с указанной даты
            commits = self.project.commits.list(
                all=True, 
                since=since_commit_date,
                order_by='created_at',
                sort='desc'
            )
            
            if not commits:
                return {
                    'has_changes': False,
                    'message': 'Нет коммитов с указанной даты',
                    'since_commit_id': None,
                    'current_commit_id': None,
                    'since_commit_date': since_commit_date,
                    'current_commit_date': None
                }
            
            # Проверяем, есть ли файл в последнем коммите
            current_commit = commits[0]
            try:
                self.project.files.get(file_path, ref=current_commit.id)
                current_commit_id = current_commit.id
                current_commit_date = current_commit.created_at
            except Exception:
                # Файл не существует в текущем коммите
                return {
                    'has_changes': False,
                    'message': f'Файл {file_path} не найден в репозитории',
                    'since_commit_id': None,
                    'current_commit_id': None,
                    'since_commit_date': since_commit_date,
                    'current_commit_date': None
                }
            
            # Ищем коммит, где файл был изменен последний раз до указанной даты
            since_commit_id = None
            since_commit_date = since_commit_date
            
            for commit in commits[1:]:  # Пропускаем первый коммит (уже проверили)
                try:
                    # Проверяем, есть ли файл в этом коммите
                    self.project.files.get(file_path, ref=commit.id)
                    since_commit_id = commit.id
                    since_commit_date = commit.created_at
                    break
                except Exception:
                    # Файл не существует в этом коммите, продолжаем поиск
                    continue
            
            # Если не нашли предыдущий коммит с файлом, используем первый коммит
            if since_commit_id is None:
                since_commit_id = commits[-1].id if commits else None
                since_commit_date = commits[-1].created_at if commits else since_commit_date
            
            return {
                'has_changes': True,
                'since_commit_id': since_commit_id,
                'current_commit_id': current_commit_id,
                'since_commit_date': since_commit_date,
                'current_commit_date': current_commit_date
            }
            
        except Exception as e:
            raise Exception(f'Error getting file changes since {since_commit_date}: {str(e)}')