#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import logging
from datetime import datetime

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database import DatabaseManager
from services.okdesk_api import OkdeskAPI
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class FixVerificationReport:
    """Класс для генерации отчета о проверке исправлений"""
    
    def __init__(self):
        self.db = DatabaseManager('okdesk_bot.db')
        self.api = None
        self.report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "database_status": {},
            "api_status": {},
            "fixes_verification": {
                "client_binding": {
                    "status": None,
                    "details": []
                },
                "comment_author": {
                    "status": None,
                    "details": []
                }
            }
        }
    
    async def generate_report(self):
        """Основная функция генерации отчета"""
        
        logger.info("🔍 Начало генерации отчета о проверке исправлений")
        
        try:
            # Подключение к API
            self.api = OkdeskAPI()
            
            # Проверка структуры БД
            self._check_database()
            
            # Проверка API подключения
            await self._check_api_connection()
            
            # Проверка исправлений привязки клиентов
            await self._verify_client_binding_fix()
            
            # Проверка исправлений с авторами комментариев
            await self._verify_comment_author_fix()
            
            # Сохранение отчета
            self._save_report()
            
            return self.report
            
        finally:
            if self.api:
                await self.api.close()
            self.db.close()
    
    def _check_database(self):
        """Проверка структуры базы данных"""
        
        logger.info("Проверка структуры базы данных")
        
        # Проверка наличия файла БД
        db_exists = os.path.exists('okdesk_bot.db')
        self.report["database_status"]["file_exists"] = db_exists
        
        if not db_exists:
            logger.error("❌ Файл базы данных не найден")
            return
            
        # Проверка таблиц
        try:
            # Получаем список таблиц в БД
            tables = self.db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            
            self.report["database_status"]["tables"] = [table[0] for table in tables]
            
            # Проверяем наличие необходимых таблиц
            required_tables = ["users", "issues", "comments"]
            for table in required_tables:
                if table not in [t[0] for t in tables]:
                    logger.error(f"❌ Таблица {table} отсутствует в базе данных")
                    
            # Проверяем количество записей в таблицах
            table_counts = {}
            for table in self.report["database_status"]["tables"]:
                count = self.db.fetch_one(f"SELECT COUNT(*) FROM {table}")[0]
                table_counts[table] = count
                
            self.report["database_status"]["record_counts"] = table_counts
            
            # Проверяем структуру таблиц
            self._check_table_structure("users")
            self._check_table_structure("issues")
            self._check_table_structure("comments")
            
            logger.info("✅ Проверка структуры базы данных завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке базы данных: {e}")
            self.report["database_status"]["error"] = str(e)
    
    def _check_table_structure(self, table_name):
        """Проверка структуры таблицы"""
        
        try:
            columns = self.db.fetch_all(f"PRAGMA table_info({table_name})")
            self.report["database_status"]["structure"] = self.report["database_status"].get("structure", {})
            self.report["database_status"]["structure"][table_name] = [
                {"name": col[1], "type": col[2]} for col in columns
            ]
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке структуры таблицы {table_name}: {e}")
    
    async def _check_api_connection(self):
        """Проверка подключения к API"""
        
        logger.info("Проверка подключения к API")
        
        try:
            # Проверяем доступность API
            companies = await self.api.get_companies_list(per_page=1)
            
            if companies:
                logger.info("✅ API подключение работает")
                self.report["api_status"]["connection"] = "ok"
                self.report["api_status"]["companies_available"] = True
            else:
                logger.error("❌ API не возвращает данные о компаниях")
                self.report["api_status"]["connection"] = "no_data"
                self.report["api_status"]["companies_available"] = False
                
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке API: {e}")
            self.report["api_status"]["connection"] = "error"
            self.report["api_status"]["error"] = str(e)
    
    async def _verify_client_binding_fix(self):
        """Проверка исправления привязки клиентов к заявкам"""
        
        logger.info("Проверка исправления привязки клиентов к заявкам")
        
        try:
            # Получаем список последних заявок
            issues = await self.api.search_issues(page=1, per_page=10)
            
            if not issues:
                logger.error("❌ Не удалось получить список заявок")
                self.report["fixes_verification"]["client_binding"]["status"] = "error"
                return
                
            self.report["fixes_verification"]["client_binding"]["total_checked"] = len(issues)
            issues_with_clients = 0
            
            for issue in issues:
                issue_id = issue.get('id')
                
                # Получаем детали заявки
                issue_details = await self.api.get_issue(issue_id)
                
                if not issue_details:
                    logger.warning(f"⚠️ Не удалось получить детали заявки {issue_id}")
                    continue
                
                client_info = {}
                
                # Проверяем наличие контакта
                if 'contact' in issue_details and issue_details['contact']:
                    client_info["contact"] = {
                        "id": issue_details['contact'].get('id'),
                        "name": issue_details['contact'].get('name')
                    }
                    issues_with_clients += 1
                
                # Проверяем наличие компании
                if 'company' in issue_details and issue_details['company']:
                    client_info["company"] = {
                        "id": issue_details['company'].get('id'),
                        "name": issue_details['company'].get('name')
                    }
                
                # Добавляем информацию о заявке в отчет
                self.report["fixes_verification"]["client_binding"]["details"].append({
                    "issue_id": issue_id,
                    "subject": issue_details.get('subject'),
                    "has_client": bool('contact' in issue_details and issue_details['contact']),
                    "client_info": client_info
                })
            
            # Определяем статус исправления
            binding_ratio = issues_with_clients / len(issues) if issues else 0
            
            if binding_ratio > 0.8:  # Если больше 80% заявок имеют клиентов, считаем исправление успешным
                self.report["fixes_verification"]["client_binding"]["status"] = "fixed"
                logger.info(f"✅ Исправление привязки клиентов работает ({binding_ratio:.0%} заявок имеют клиентов)")
            elif binding_ratio > 0.5:  # Если от 50% до 80%, считаем частичным исправлением
                self.report["fixes_verification"]["client_binding"]["status"] = "partial"
                logger.warning(f"⚠️ Исправление привязки клиентов работает частично ({binding_ratio:.0%} заявок имеют клиентов)")
            else:  # Если меньше 50%, считаем что исправление не работает
                self.report["fixes_verification"]["client_binding"]["status"] = "not_fixed"
                logger.error(f"❌ Исправление привязки клиентов не работает ({binding_ratio:.0%} заявок имеют клиентов)")
            
            self.report["fixes_verification"]["client_binding"]["binding_ratio"] = binding_ratio
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке исправления привязки клиентов: {e}")
            self.report["fixes_verification"]["client_binding"]["status"] = "error"
            self.report["fixes_verification"]["client_binding"]["error"] = str(e)
    
    async def _verify_comment_author_fix(self):
        """Проверка исправления авторов комментариев"""
        
        logger.info("Проверка исправления авторов комментариев")
        
        try:
            # Получаем список последних заявок
            issues = await self.api.search_issues(page=1, per_page=5)
            
            if not issues:
                logger.error("❌ Не удалось получить список заявок")
                self.report["fixes_verification"]["comment_author"]["status"] = "error"
                return
            
            total_comments = 0
            comments_with_authors = 0
            
            for issue in issues:
                issue_id = issue.get('id')
                
                # Получаем комментарии заявки
                comments = await self.api.get_issue_comments(issue_id)
                
                if not comments:
                    continue
                    
                total_comments += len(comments)
                
                for comment in comments:
                    comment_id = comment.get('id')
                    has_author = bool('author' in comment and comment['author'])
                    
                    if has_author:
                        comments_with_authors += 1
                    
                    # Добавляем информацию о комментарии в отчет
                    self.report["fixes_verification"]["comment_author"]["details"].append({
                        "comment_id": comment_id,
                        "issue_id": issue_id,
                        "has_author": has_author,
                        "author_info": comment.get('author', {})
                    })
            
            # Определяем статус исправления
            self.report["fixes_verification"]["comment_author"]["total_checked"] = total_comments
            
            if total_comments == 0:
                logger.warning("⚠️ Комментарии не найдены")
                self.report["fixes_verification"]["comment_author"]["status"] = "unknown"
                return
                
            author_ratio = comments_with_authors / total_comments
            
            if author_ratio > 0.8:  # Если больше 80% комментариев имеют авторов, считаем исправление успешным
                self.report["fixes_verification"]["comment_author"]["status"] = "fixed"
                logger.info(f"✅ Исправление авторов комментариев работает ({author_ratio:.0%} комментариев имеют авторов)")
            elif author_ratio > 0.5:  # Если от 50% до 80%, считаем частичным исправлением
                self.report["fixes_verification"]["comment_author"]["status"] = "partial"
                logger.warning(f"⚠️ Исправление авторов комментариев работает частично ({author_ratio:.0%} комментариев имеют авторов)")
            else:  # Если меньше 50%, считаем что исправление не работает
                self.report["fixes_verification"]["comment_author"]["status"] = "not_fixed"
                logger.error(f"❌ Исправление авторов комментариев не работает ({author_ratio:.0%} комментариев имеют авторов)")
            
            self.report["fixes_verification"]["comment_author"]["author_ratio"] = author_ratio
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке исправления авторов комментариев: {e}")
            self.report["fixes_verification"]["comment_author"]["status"] = "error"
            self.report["fixes_verification"]["comment_author"]["error"] = str(e)
    
    def _save_report(self):
        """Сохранение отчета в JSON файл"""
        
        report_file = f"fix_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
                
            logger.info(f"✅ Отчет сохранен в файл: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении отчета: {e}")

async def main():
    """Главная функция"""
    
    logger.info("🚀 Запуск проверки исправлений")
    
    report_generator = FixVerificationReport()
    report = await report_generator.generate_report()
    
    # Выводим краткий итог
    logger.info("\n📋 Краткий итог проверки:")
    
    client_binding_status = report["fixes_verification"]["client_binding"]["status"]
    comment_author_status = report["fixes_verification"]["comment_author"]["status"]
    
    if client_binding_status == "fixed":
        logger.info("✅ Исправление привязки клиентов: РАБОТАЕТ")
    elif client_binding_status == "partial":
        logger.info("⚠️ Исправление привязки клиентов: ЧАСТИЧНО РАБОТАЕТ")
    else:
        logger.info("❌ Исправление привязки клиентов: НЕ РАБОТАЕТ")
        
    if comment_author_status == "fixed":
        logger.info("✅ Исправление авторов комментариев: РАБОТАЕТ")
    elif comment_author_status == "partial":
        logger.info("⚠️ Исправление авторов комментариев: ЧАСТИЧНО РАБОТАЕТ")
    elif comment_author_status == "unknown":
        logger.info("❓ Исправление авторов комментариев: НЕИЗВЕСТНО (комментарии не найдены)")
    else:
        logger.info("❌ Исправление авторов комментариев: НЕ РАБОТАЕТ")
    
    return report

if __name__ == "__main__":
    asyncio.run(main())
