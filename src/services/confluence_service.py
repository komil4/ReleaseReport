import os
from atlassian import Confluence
from typing import List, Dict, Any
from datetime import datetime
from .config_manager import ConfigManager
import re

class ConfluenceService:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

        confluence_config = self.config_manager.get_confluence_config()  
        
        self.confluence_url = confluence_config['url']
        self.confluence_email = confluence_config['email']
        self.confluence_token = confluence_config['api_token']
        self.space_key = confluence_config['space_key']
        self.parent_id = confluence_config['parent_id']
        
        if not all([self.confluence_url, self.confluence_email, self.confluence_token, self.space_key]):
            raise ValueError('Confluence configuration is missing')
        
        self.confluence = Confluence(
            url=self.confluence_url,
            token=self.confluence_token
        )
    
    def create_report_page(self, commit_data: List[Dict], task_data: List[Dict], report_service=None, metadata_changes: Dict[str, Any] = None) -> str:
        try:
            # Создаем HTML таблицы для отчета используя report_service
            if report_service:
                html_content = report_service.generate_confluence_html_report(
                    commit_data, task_data, metadata_changes
                )
            else:
                # Fallback к старому методу если report_service не передан
                html_content = self._generate_html_report(commit_data, task_data)
            
            # Создаем страницу в Confluence
            page_title = f'Отчет о релизе - {datetime.now().strftime("%Y-%m-%d")}'
            
            result = self.confluence.create_page(
                space=self.space_key,
                title=page_title,
                body=html_content,
                type='page',
                parent_id=self.parent_id
            )
            
            page_url = f'{self.confluence_url}{result["_links"]["webui"]}'
            return page_url
            
        except Exception as e:
            raise Exception(f'Error creating Confluence page: {str(e)}')
    
    def get_page_title_by_url(self, url: str) -> str:
        """Получает заголовок страницы Confluence по URL"""
        try:
            # Извлекаем ID страницы из URL
            # URL обычно имеет формат: https://confluence.domain.com/pages/viewpage.action?pageId=123456
            page_id_match = re.search(r'pageId=(\d+)', url)
            if page_id_match:
                page_id = page_id_match.group(1)
                page = self.confluence.get_page_by_id(page_id, expand='version')
                return page.get('title', 'Unknown Page')
            
            # Альтернативный формат URL: https://confluence.domain.com/display/SPACE/Page+Title
            space_title_match = re.search(r'/display/[^/]+/([^?]+)', url)
            if space_title_match:
                page_title = space_title_match.group(1).replace('+', ' ')
                return page_title
            
            # Если не удалось извлечь ID или название, возвращаем базовое название
            return 'Confluence Page'
            
        except Exception as e:
            print(f'Error getting page title for URL {url}: {str(e)}')
            return 'Confluence Page'

    def _get_confluence_attachments(self, task_number: str, task_data: Dict) -> List[Dict[str, str]]:
        """Получает прикрепленные к задаче страницы Confluence"""
        try:
            confluence_pages = []
            
            # Ищем ссылки на Confluence в описании задачи
            description = task_data.get('description', '')
            if description:
                import re
                confluence_urls = []
                for match in re.findall(r'https?://[^/]*confluence[^/]*/[^\s<>"\']*', description):
                    # Обрезаем ссылку до pageId=число, если есть
                    pageid_match = re.search(r'(pageId=\d+)', match)
                    if pageid_match:
                        trimmed_url = match[:match.find(pageid_match.group(1)) + len(pageid_match.group(1))]
                        confluence_urls.append(trimmed_url)
                    else:
                        confluence_urls.append(match)
                
                for url in confluence_urls:
                    confluence_pages.append({
                        'filename': self.get_page_title_by_url(url),
                        'url': url,
                        'created': 'Unknown',
                        'author': 'Unknown'
                    })
            
            # Ищем прикрепленные файлы (если 1C поддерживает)
            attachments = task_data.get('attachments', [])
            if attachments:
                for attachment in attachments:
                    if (attachment.get('filename', '').endswith('.html') or 
                        attachment.get('filename', '').endswith('.htm') or
                        'confluence' in attachment.get('filename', '').lower()):
                        
                        confluence_pages.append({
                            'filename': attachment.get('filename', 'Unknown'),
                            'url': attachment.get('url', ''),
                            'created': attachment.get('created', 'Unknown'),
                            'author': attachment.get('author', 'Unknown')
                        })
            
            return confluence_pages
            
        except Exception as e:
            print(f'Error fetching Confluence attachments for task {task_number}: {str(e)}')
            return []