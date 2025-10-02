"""
Генератор HTML отчетов
"""
from typing import List, Optional
from datetime import datetime
from .base import ReportGenerator, CommitData, TaskData, MetadataChanges
from .constants import HTML_TEMPLATES, CSS_CLASSES, METADATA_ELEMENT_TYPES, MESSAGES, STYLE_SETTINGS


class HTMLReportGenerator(ReportGenerator):
    """Генератор HTML отчетов"""
    
    def generate(self, commits: List[CommitData], tasks: List[TaskData], 
                metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует HTML отчет"""
        return self._generate_full_html_report(commits, tasks, metadata)
    
    def _generate_full_html_report(self, commits: List[CommitData], tasks: List[TaskData], 
                                 metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует полный HTML отчет"""
        html = f"""
        {HTML_TEMPLATES['DOCTYPE']}
        <html lang="ru">
        <head>
            {HTML_TEMPLATES['META_CHARSET']}
            {HTML_TEMPLATES['META_VIEWPORT']}
            <title>Отчет о релизе - {datetime.now().strftime('%d.%m.%Y %H:%M')}</title>
            {self._generate_css_styles()}
        </head>
        <body>
            <div class="{CSS_CLASSES['container']}">
                {self._generate_header()}
                <div class="{CSS_CLASSES['content']}">
                    {self._generate_stats_section(commits, tasks, metadata)}
                    {self._generate_commits_section(commits, tasks)}
                    {self._generate_tasks_section(tasks)}
                    {self._generate_metadata_section(metadata) if metadata and metadata.has_changes else self._generate_metadata_debug_info(metadata)}
                </div>
                {self._generate_footer()}
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_css_styles(self) -> str:
        """Генерирует CSS стили"""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 300;
            }
            .header .subtitle {
                margin-top: 10px;
                opacity: 0.9;
                font-size: 1.1rem;
            }
            .content {
                padding: 30px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                border-left: 4px solid #667eea;
            }
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }
            .stat-label {
                color: #666;
                font-size: 0.9rem;
            }
            .section {
                margin-bottom: 40px;
            }
            .section h2 {
                color: #333;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .commits-list {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
            }
            .commit-item {
                background: white;
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 6px;
                border-left: 4px solid #28a745;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .commit-hash {
                font-family: 'Courier New', monospace;
                background: #e9ecef;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 0.85rem;
                color: #495057;
            }
            .commit-message {
                margin: 8px 0;
                font-weight: 500;
            }
            .commit-meta {
                font-size: 0.9rem;
                color: #666;
            }
            .task-link {
                color: #667eea;
                text-decoration: none;
                font-weight: 500;
            }
            .task-link:hover {
                text-decoration: underline;
            }
            .commit-link {
                color: #333;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.3s ease;
            }
            .commit-link:hover {
                color: #667eea;
                text-decoration: underline;
            }
            .commit-item-link {
                text-decoration: none;
                color: inherit;
                display: block;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .commit-item-link:hover {
                transform: translateY(-2px);
            }
            .commit-item-link:hover .commit-item {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                border-left-color: #667eea;
            }
            .task-number {
                color: #667eea;
                font-weight: 500;
            }
            .task-item-link {
                text-decoration: none;
                color: inherit;
                display: block;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .task-item-link:hover {
                transform: translateY(-2px);
            }
            .task-item-link:hover .task-item {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                border-left-color: #ffc107;
            }
            .tasks-list {
                display: grid;
                gap: 15px;
            }
            .task-item {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
            }
            .task-title {
                font-weight: bold;
                margin-bottom: 8px;
                color: #333;
            }
            .task-description {
                color: #666;
                margin-bottom: 10px;
            }
            .task-meta {
                font-size: 0.9rem;
                color: #666;
            }
            .footer {
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
                border-top: 1px solid #dee2e6;
            }
            .no-data {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 40px;
            }
        </style>
        """
    
    def _generate_header(self) -> str:
        """Генерирует заголовок отчета"""
        return f"""
        <div class="{CSS_CLASSES['header']}">
            <h1>📊 Отчет о релизе</h1>
            <div class="subtitle">Сформирован {datetime.now().strftime('%d.%m.%Y в %H:%M')}</div>
        </div>
        """
    
    def _generate_stats_section(self, commits: List[CommitData], tasks: List[TaskData], metadata: Optional[MetadataChanges] = None) -> str:
        """Генерирует секцию статистики"""
        stats_html = f"""
        <div class="{CSS_CLASSES['stats']}">
            <div class="{CSS_CLASSES['stat_card']}">
                <div class="{CSS_CLASSES['stat_number']}">{len(commits)}</div>
                <div class="{CSS_CLASSES['stat_label']}">Коммитов</div>
            </div>
            <div class="{CSS_CLASSES['stat_card']}">
                <div class="{CSS_CLASSES['stat_number']}">{len(tasks)}</div>
                <div class="{CSS_CLASSES['stat_label']}">Задач</div>
            </div>
        """
        
        # Добавляем статистику метаданных, если есть изменения
        if metadata and metadata.has_changes and metadata.summary:
            total_metadata_changes = (metadata.summary.get('total_added', 0) + 
                                    metadata.summary.get('total_removed', 0) + 
                                    metadata.summary.get('total_modified', 0))
            
            stats_html += f"""
            <div class="{CSS_CLASSES['stat_card']}">
                <div class="{CSS_CLASSES['stat_number']}">{total_metadata_changes}</div>
                <div class="{CSS_CLASSES['stat_label']}">Изменений метаданных</div>
            </div>
            """
        
        stats_html += """
        </div>
        """
        return stats_html
    
    def _generate_commits_section(self, commits: List[CommitData], tasks: List[TaskData]) -> str:
        """Генерирует секцию коммитов"""
        html = f"""
        <div class="{CSS_CLASSES['section']}">
            <h2>📝 Коммиты</h2>
            <div class="{CSS_CLASSES['commits_list']}">
        """
        
        if commits:
            for commit in commits:
                task_url = self._find_task_url(commit.task_number, tasks)
                
                # Если есть URL коммита, делаем весь блок кликабельным
                if commit.url:
                    task_link_html = ""
                    if commit.task_number and task_url:
                        task_link_html = f' | <a href="{task_url}" class="{CSS_CLASSES["task_link"]}" onclick="event.stopPropagation()">Задача: {commit.task_number}</a>'
                    elif commit.task_number:
                        task_link_html = f' | <span class="task-number">Задача: {commit.task_number}</span>'
                    
                    html += f"""
                    <a href="{commit.url}" target="_blank" class="commit-item-link">
                        <div class="{CSS_CLASSES['commit_item']}">
                            <div class="{CSS_CLASSES['commit_hash']}">{commit.id[:8]}</div>
                            <div class="{CSS_CLASSES['commit_message']}">{commit.message}</div>
                            <div class="{CSS_CLASSES['commit_meta']}">
                                Автор: {commit.author} | 
                                Дата: {commit.date}
                                {task_link_html}
                            </div>
                        </div>
                    </a>
                    """
                else:
                    # Если нет URL, отображаем как обычный блок
                    html += f"""
                    <div class="{CSS_CLASSES['commit_item']}">
                        <div class="{CSS_CLASSES['commit_hash']}">{commit.id[:8]}</div>
                        <div class="{CSS_CLASSES['commit_message']}">{commit.message}</div>
                        <div class="{CSS_CLASSES['commit_meta']}">
                            Автор: {commit.author} | 
                            Дата: {commit.date}
                            {f' | <a href="{task_url}" class="{CSS_CLASSES["task_link"]}">Задача: {commit.task_number}</a>' if commit.task_number else ''}
                        </div>
                    </div>
                    """
        else:
            html += f'<div class="{CSS_CLASSES["no_data"]}">Нет коммитов для отображения</div>'
        
        html += """
            </div>
        </div>
        """
        return html
    
    def _generate_tasks_section(self, tasks: List[TaskData]) -> str:
        """Генерирует секцию задач"""
        html = f"""
        <div class="{CSS_CLASSES['section']}">
            <h2>🎯 Задачи</h2>
            <div class="{CSS_CLASSES['tasks_list']}">
        """
        
        if tasks:
            for task in tasks:
                # Формируем информацию о задаче интрасервис
                intraservice_info = ""
                if task.intraservice_task:
                    if task.intraservice_task_url:
                        intraservice_info = f'<br><span class="intraservice-task">Задача интрасервис: <a href="{task.intraservice_task_url}" target="_blank">{task.intraservice_task}</a></span>'
                    else:
                        intraservice_info = f'<br><span class="intraservice-task">Задача интрасервис: {task.intraservice_task}</span>'
                
                if task.url:
                    html += f"""
                    <a href="{task.url}" target="_blank" class="task-item-link">
                        <div class="{CSS_CLASSES['task_item']}">
                            <div class="{CSS_CLASSES['task_title']}">{task.summary}</div>
                            <div class="{CSS_CLASSES['task_description']}">{task.description}</div>
                            <div class="{CSS_CLASSES['task_meta']}">
                                ID: {task.task_number} | 
                                Статус: {task.status} | 
                                Приоритет: {task.priority}
                                {intraservice_info}
                            </div>
                        </div>
                    </a>
                    """
                else:
                    html += f"""
                    <div class="{CSS_CLASSES['task_item']}">
                        <div class="{CSS_CLASSES['task_title']}">{task.summary}</div>
                        <div class="{CSS_CLASSES['task_description']}">{task.description}</div>
                        <div class="{CSS_CLASSES['task_meta']}">
                            ID: {task.task_number} | 
                            Статус: {task.status} | 
                            Приоритет: {task.priority}
                            {intraservice_info}
                        </div>
                    </div>
                    """
        else:
            html += f'<div class="{CSS_CLASSES["no_data"]}">{MESSAGES["no_tasks"]}</div>'
        
        html += """
            </div>
        </div>
        """
        return html
    
    def _generate_metadata_section(self, metadata: MetadataChanges) -> str:
        """Генерирует секцию метаданных"""
        html = f"""
        <div class="{CSS_CLASSES['section']}">
            <h2>📋 Изменения метаданных подсистемы</h2>
            <div class="{CSS_CLASSES['commits_list']}">
        """
        
        # Информация о периоде
        html += f"""
        <div class="{CSS_CLASSES['commit_item']}">
            <div class="{CSS_CLASSES['commit_message']}">📄 Файл: src/cf/Configuration.xml</div>
            <div class="{CSS_CLASSES['commit_meta']}">
                📅 Период: с {metadata.since_commit_date or 'Неизвестно'} по {metadata.current_commit_date or 'Неизвестно'}
            </div>
        </div>
        """
        
        # Сводка изменений
        if metadata.summary:
            total_changes = (metadata.summary.get('total_added', 0) + 
                           metadata.summary.get('total_removed', 0) + 
                           metadata.summary.get('total_modified', 0))
            
            html += f"""
            <div class="{CSS_CLASSES['commit_item']}">
                <div class="{CSS_CLASSES['commit_message']}">📊 Сводка изменений</div>
                <div class="{CSS_CLASSES['commit_meta']}">
                    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                        <span style="color: #28a745;">➕ Добавлено: {metadata.summary.get('total_added', 0)}</span>
                        <span style="color: #dc3545;">➖ Удалено: {metadata.summary.get('total_removed', 0)}</span>
                        <span style="color: #ffc107;">✏️ Изменено: {metadata.summary.get('total_modified', 0)}</span>
                        <span style="color: #6c757d; font-weight: bold;">📈 Всего: {total_changes}</span>
                    </div>
                </div>
            </div>
            """
        
        # Детали изменений
        html += self._generate_metadata_details(metadata)
        
        html += """
            </div>
        </div>
        """
        return html
    
    def _generate_metadata_details(self, metadata: MetadataChanges) -> str:
        """Генерирует детали изменений метаданных"""
        html = ""
        
        # Добавленные элементы
        if metadata.added_metadata:
            html += f"""
            <div class="{CSS_CLASSES['commit_item']}">
                <div class="{CSS_CLASSES['commit_message']}" style="color: #28a745;">➕ Добавленные элементы ({len(metadata.added_metadata)})</div>
                <div class="{CSS_CLASSES['commit_meta']}">
            """
            for element in metadata.added_metadata:
                elem_type = METADATA_ELEMENT_TYPES.get(element['tag'], element['tag'])
                elem_name = element.text if hasattr(element, 'text') else element.get('text', '')
                elem_path = element.path if hasattr(element, 'path') else element.get('path', '')
                html += f"""
                <div style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #28a745;">
                    <div style="font-weight: 600; color: #28a745;">{elem_type}</div>
                    <div style="color: #333;">{elem_name}</div>
                    {f'<div style="font-size: 0.9em; color: #6c757d;">Путь: {elem_path}</div>' if elem_path else ''}
                </div>"""
            html += """
                </div>
            </div>
            """
        
        # Удаленные элементы
        if metadata.removed_metadata:
            html += f"""
            <div class="{CSS_CLASSES['commit_item']}">
                <div class="{CSS_CLASSES['commit_message']}" style="color: #dc3545;">➖ Удаленные элементы ({len(metadata.removed_metadata)})</div>
                <div class="{CSS_CLASSES['commit_meta']}">
            """
            for element in metadata.removed_metadata:
                elem_type = METADATA_ELEMENT_TYPES.get(element['tag'], element['tag'])
                elem_name = element.text if hasattr(element, 'text') else element.get('text', '')
                elem_path = element.path if hasattr(element, 'path') else element.get('path', '')
                html += f"""
                <div style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #dc3545;">
                    <div style="font-weight: 600; color: #dc3545;">{elem_type}</div>
                    <div style="color: #333;">{elem_name}</div>
                    {f'<div style="font-size: 0.9em; color: #6c757d;">Путь: {elem_path}</div>' if elem_path else ''}
                </div>"""
            html += """
                </div>
            </div>
            """
        
        # Измененные элементы
        if metadata.modified_metadata:
            html += f"""
            <div class="{CSS_CLASSES['commit_item']}">
                <div class="{CSS_CLASSES['commit_message']}" style="color: #ffc107;">✏️ Измененные элементы ({len(metadata.modified_metadata)})</div>
                <div class="{CSS_CLASSES['commit_meta']}">
            """
            for element in metadata.modified_metadata:
                elem_type = METADATA_ELEMENT_TYPES.get(element['tag'], element['tag'])
                elem_name = element.text if hasattr(element, 'text') else element.get('text', '')
                elem_path = element.path if hasattr(element, 'path') else element.get('path', '')
                
                # Показываем изменения, если они есть
                changes_info = ""
                if hasattr(element, 'changes') and element.changes:
                    changes_info = f"<div style='font-size: 0.9em; color: #6c757d; margin-top: 4px;'>Изменения: {', '.join(element.changes)}</div>"
                
                html += f"""
                <div style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #ffc107;">
                    <div style="font-weight: 600; color: #ffc107;">{elem_type}</div>
                    <div style="color: #333;">{elem_name}</div>
                    {f'<div style="font-size: 0.9em; color: #6c757d;">Путь: {elem_path}</div>' if elem_path else ''}
                    {changes_info}
                </div>"""
            html += """
                </div>
            </div>
            """
        
        return html
    
    
    def _generate_metadata_debug_info(self, metadata: Optional[MetadataChanges]) -> str:
        """Генерирует отладочную информацию о метаданных"""
        if metadata is None:
            return f"""
            <div class="{CSS_CLASSES['section']}">
                <h2>📋 Изменения метаданных подсистемы</h2>
                <div class="{CSS_CLASSES['commits_list']}">
                    <div class="{CSS_CLASSES['commit_item']}">
                        <div class="{CSS_CLASSES['commit_message']}" style="color: #6c757d;">⚠️ Метаданные не анализировались (metadata is None)</div>
                    </div>
                </div>
            </div>
            """
        elif not metadata.has_changes:
            return f"""
            <div class="{CSS_CLASSES['section']}">
                <h2>📋 Изменения метаданных подсистемы</h2>
                <div class="{CSS_CLASSES['commits_list']}">
                    <div class="{CSS_CLASSES['commit_item']}">
                        <div class="{CSS_CLASSES['commit_message']}" style="color: #6c757d;">ℹ️ Нет изменений в метаданных (has_changes=False)</div>
                    </div>
                </div>
            </div>
            """
        else:
            return ""
    
    def _generate_footer(self) -> str:
        """Генерирует подвал отчета"""
        return f"""
        <div class="{CSS_CLASSES['footer']}">
            <p>{MESSAGES['report_generated']}</p>
        </div>
        """
    
    def _find_task_url(self, task_number: Optional[str], tasks: List[TaskData]) -> str:
        """Находит URL задачи по номеру"""
        if not task_number or not tasks:
            return '#'
        
        for task in tasks:
            if task.task_number == task_number:
                return task.url
        return '#'
    
    def generate_empty_report(self, message: str) -> str:
        """Генерирует пустой отчет"""
        return f"""
        {HTML_TEMPLATES['DOCTYPE']}
        <html lang="ru">
        <head>
            {HTML_TEMPLATES['META_CHARSET']}
            <title>Отчет о релизе</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; background: #f5f5f5; }}
                .container {{ background: white; padding: 40px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
                .icon {{ font-size: 4rem; margin-bottom: 20px; }}
                .message {{ color: #666; font-size: 1.2rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📊</div>
                <div class="message">{message}</div>
            </div>
        </body>
        </html>
        """
    
    def generate_error_report(self, error_message: str) -> str:
        """Генерирует отчет с ошибкой"""
        return f"""
        {HTML_TEMPLATES['DOCTYPE']}
        <html lang="ru">
        <head>
            {HTML_TEMPLATES['META_CHARSET']}
            <title>Ошибка формирования отчета</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; background: #f5f5f5; }}
                .container {{ background: #f8d7da; color: #721c24; padding: 40px; border-radius: 10px; max-width: 600px; margin: 0 auto; border: 1px solid #f5c6cb; }}
                .icon {{ font-size: 4rem; margin-bottom: 20px; }}
                .message {{ font-size: 1.2rem; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⚠️</div>
                <div class="message">{error_message}</div>
            </div>
        </body>
        </html>
        """
