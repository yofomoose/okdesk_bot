#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Класс для управления базой данных SQLite"""
    
    def __init__(self, db_path):
        """Инициализация подключения к базе данных
        
        Args:
            db_path: путь к файлу базы данных
        """
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
        # Проверяем, существует ли файл базы данных
        db_exists = os.path.exists(db_path)
        
        # Подключаемся к базе данных
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        
        # Если база данных только что создана, инициализируем таблицы
        if not db_exists:
            self._init_tables()
    
    def _init_tables(self):
        """Инициализация таблиц в новой базе данных"""
        
        logger.info(f"Инициализация таблиц в новой базе данных: {self.db_path}")
        
        # Таблица пользователей
        self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                created_at INTEGER,
                okdesk_contact_id INTEGER,
                company_id INTEGER,
                inn TEXT,
                email TEXT,
                additional_info TEXT
            )
        """)
        
        # Таблица заявок
        self.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                issue_id INTEGER PRIMARY KEY,
                telegram_id TEXT,
                created_at INTEGER,
                status TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Таблица комментариев
        self.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id INTEGER PRIMARY KEY,
                issue_id INTEGER,
                telegram_id TEXT,
                content TEXT,
                created_at INTEGER,
                FOREIGN KEY (issue_id) REFERENCES issues(issue_id),
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Сохраняем изменения
        self.commit()
        
        logger.info("Таблицы успешно созданы")
    
    def execute(self, query, params=None):
        """Выполнение SQL-запроса
        
        Args:
            query: SQL-запрос
            params: параметры для запроса (опционально)
        
        Returns:
            Cursor: курсор SQLite
        """
        try:
            if params:
                return self.cursor.execute(query, params)
            else:
                return self.cursor.execute(query)
        except sqlite3.Error as e:
            logger.error(f"Ошибка выполнения SQL-запроса: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            raise
    
    def executemany(self, query, params_list):
        """Выполнение SQL-запроса для множества параметров
        
        Args:
            query: SQL-запрос
            params_list: список наборов параметров
        
        Returns:
            Cursor: курсор SQLite
        """
        try:
            return self.cursor.executemany(query, params_list)
        except sqlite3.Error as e:
            logger.error(f"Ошибка выполнения множественного SQL-запроса: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Количество параметров: {len(params_list)}")
            raise
    
    def commit(self):
        """Фиксация изменений в базе данных"""
        try:
            self.connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при коммите изменений: {e}")
            raise
    
    def rollback(self):
        """Откат изменений в базе данных"""
        try:
            self.connection.rollback()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при откате изменений: {e}")
            raise
    
    def fetch_one(self, query, params=None):
        """Получение одной записи
        
        Args:
            query: SQL-запрос
            params: параметры для запроса (опционально)
        
        Returns:
            tuple: запись из базы данных или None
        """
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query, params=None):
        """Получение всех записей
        
        Args:
            query: SQL-запрос
            params: параметры для запроса (опционально)
        
        Returns:
            list: список записей из базы данных
        """
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
    
    def __enter__(self):
        """Поддержка контекстного менеджера (with)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения при выходе из контекстного менеджера"""
        self.close()
    
    def __del__(self):
        """Деструктор для закрытия соединения"""
        self.close()
