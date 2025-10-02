import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple
from .gitlab_service import GitLabService
from .config_manager import ConfigManager
import re

class MetadataService:
    def __init__(self, config_service: ConfigManager):
        self.config_service = config_service
        self.gitlab_service = GitLabService(config_service)
    
    def analyze_metadata_changes(self, since_commit_date: str = None) -> Dict[str, Any]:
        """
        Анализирует изменения метаданных подсистемы в файле Configuration.xml
        
        Args:
            since_commit_date: дата коммита для начала отслеживания изменений
        
        Returns:
            Словарь с информацией об изменениях метаданных
        """
        try:
            # Получаем изменения файла Configuration.xml
            file_changes = self.gitlab_service.get_file_changes_since(
                file_path='src/cf/Configuration.xml',
                since_commit_date=since_commit_date
            )
            
            if not file_changes['has_changes']:
                return {
                    'has_changes': False,
                    'message': 'Нет изменений в метаданных подсистемы',
                    'added_metadata': [],
                    'removed_metadata': [],
                    'modified_metadata': []
                }
            
            # Получаем содержимое файла до и после изменений
            old_content = self._get_file_content_at_commit(file_changes['since_commit_id'])
            new_content = self._get_file_content_at_commit(file_changes['current_commit_id'])
            
            # Анализируем изменения
            analysis_result = self._analyze_xml_changes(old_content, new_content)
            
            return {
                'has_changes': True,
                'since_commit_id': file_changes['since_commit_id'],
                'current_commit_id': file_changes['current_commit_id'],
                'since_commit_date': file_changes['since_commit_date'],
                'current_commit_date': file_changes['current_commit_date'],
                'added_metadata': analysis_result['added'],
                'removed_metadata': analysis_result['removed'],
                'modified_metadata': analysis_result['modified'],
                'summary': {
                    'total_added': len(analysis_result['added']),
                    'total_removed': len(analysis_result['removed']),
                    'total_modified': len(analysis_result['modified'])
                }
            }
            
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            print(f'Warning: Error analyzing metadata changes: {str(e)}')
            return {
                'has_changes': False,
                'message': f'Ошибка анализа метаданных: {str(e)}',
                'added_metadata': [],
                'removed_metadata': [],
                'modified_metadata': []
            }
    
    def _get_file_content_at_commit(self, commit_id: str) -> str:
        """Получает содержимое файла Configuration.xml на определенном коммите"""
        try:
            file_data = self.gitlab_service.project.files.get(
                'src/cf/Configuration.xml', 
                ref=commit_id
            )
            
            import base64
            content = base64.b64decode(file_data.content).decode('utf-8')
            return content
            
        except Exception as e:
            if '404' in str(e) or 'not found' in str(e).lower():
                return ""  # Файл не существовал на этом коммите
            print(f'Warning: Error getting file content at commit {commit_id}: {str(e)}')
            return ""  # Возвращаем пустую строку вместо исключения
    
    def _analyze_xml_changes(self, old_content: str, new_content: str) -> Dict[str, List[Dict]]:
        """
        Анализирует изменения в XML файле и определяет добавленные, удаленные и измененные элементы
        """
        old_elements = self._parse_xml_elements(old_content) if old_content else {}
        new_elements = self._parse_xml_elements(new_content) if new_content else {}
        
        added = []
        removed = []
        modified = []
        
        # Находим добавленные элементы
        for element_id, element_data in new_elements.items():
            if element_id not in old_elements:
                added.append(element_data)
            elif old_elements[element_id] != element_data:
                # Элемент изменился
                modified.append({
                    'id': element_id,
                    'old_data': old_elements[element_id],
                    'new_data': element_data,
                    'changes': self._get_element_changes(old_elements[element_id], element_data)
                })
        
        # Находим удаленные элементы
        for element_id, element_data in old_elements.items():
            if element_id not in new_elements:
                removed.append(element_data)
        
        return {
            'added': added,
            'removed': removed,
            'modified': modified
        }
    
    def _parse_xml_elements(self, xml_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Парсит XML и извлекает элементы с их атрибутами и содержимым
        """
        elements = {}
        
        try:
            root = ET.fromstring(xml_content)
            
            # Рекурсивно обходим все элементы
            for element in root.iter():
                element_id = self._get_element_identifier(element)
                if element.tag == '{http://v8.1c.ru/8.3/MDClasses}Constant' \
                or element.tag == '{http://v8.1c.ru/8.3/MDClasses}Catalog' \
                or element.tag == '{http://v8.1c.ru/8.3/MDClasses}Document' \
                or element.tag == '{http://v8.1c.ru/8.3/MDClasses}InformationRegister' \
                or element.tag == '{http://v8.1c.ru/8.3/MDClasses}AccumulationRegister':
                    elements[element_id] = {
                        'id': element_id,
                        'tag': element.tag,
                        'attributes': element.attrib,
                        'text': element.text.strip() if element.text else '',
                        'children_count': len(list(element)),
                        'path': self._get_element_path(element)
                    }
        
        except ET.ParseError as e:
            print(f'Error parsing XML: {str(e)}')
            # Если XML невалидный, пытаемся извлечь информацию через регулярные выражения
            elements = self._parse_xml_with_regex(xml_content)
        
        return elements
    
    def _get_element_identifier(self, element) -> str:
        """
        Создает уникальный идентификатор для элемента на основе его атрибутов и пути
        """
        # Используем атрибуты для идентификации
        if 'id' in element.attrib:
            return f"{element.tag}@{element.attrib['id']}"
        elif 'name' in element.attrib:
            return f"{element.tag}@{element.attrib['name']}"
        elif 'type' in element.attrib:
            return f"{element.tag}@{element.attrib['type']}"
        else:
            # Используем путь и текст для идентификации
            path = self._get_element_path(element)
            text = element.text.strip() if element.text else ''
            return f"{path}#{text[:50]}" if text else path
    
    def _get_element_path(self, element) -> str:
        """Получает путь к элементу в XML"""
        path_parts = []
        current = element
        while current is not None:
            path_parts.insert(0, current.tag)
            current = current.getparent() if hasattr(current, 'getparent') else None
        return '/'.join(path_parts)
    
    def _parse_xml_with_regex(self, xml_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Альтернативный метод парсинга XML через регулярные выражения
        для случаев, когда XML невалидный
        """
        elements = {}
        
        # Паттерны для поиска элементов
        tag_pattern = r'<(\w+)([^>]*)>(.*?)</\1>'
        attr_pattern = r'(\w+)="([^"]*)"'
        
        matches = re.findall(tag_pattern, xml_content, re.DOTALL)
        
        for i, (tag, attrs_str, content) in enumerate(matches):
            # Парсим атрибуты
            attrs = dict(re.findall(attr_pattern, attrs_str))
            
            element_id = f"{tag}@{i}"
            if 'id' in attrs:
                element_id = f"{tag}@{attrs['id']}"
            elif 'name' in attrs:
                element_id = f"{tag}@{attrs['name']}"
            
            elements[element_id] = {
                'id': element_id,
                'tag': tag,
                'attributes': attrs,
                'text': content.strip(),
                'children_count': 0,
                'path': tag
            }
        
        return elements
    
    def _get_element_changes(self, old_data: Dict, new_data: Dict) -> List[str]:
        """Определяет конкретные изменения в элементе"""
        changes = []
        
        # Сравниваем атрибуты
        old_attrs = old_data.get('attributes', {})
        new_attrs = new_data.get('attributes', {})
        
        for key in set(old_attrs.keys()) | set(new_attrs.keys()):
            old_val = old_attrs.get(key, '')
            new_val = new_attrs.get(key, '')
            
            if old_val != new_val:
                if key not in old_attrs:
                    changes.append(f"Добавлен атрибут {key}='{new_val}'")
                elif key not in new_attrs:
                    changes.append(f"Удален атрибут {key}='{old_val}'")
                else:
                    changes.append(f"Изменен атрибут {key}: '{old_val}'  '{new_val}'")
        
        # Сравниваем текст
        old_text = old_data.get('text', '')
        new_text = new_data.get('text', '')
        
        if old_text != new_text:
            changes.append(f"Изменен текст: '{old_text[:100]}...'  '{new_text[:100]}...'")
        
        return changes
