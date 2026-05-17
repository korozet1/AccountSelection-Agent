import logging
from contextlib import contextmanager

import pymysql

logger = logging.getLogger("database")

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "charset": "utf8mb4",
    "use_unicode": True,
    "autocommit": True,
}

DB_NAME = "honor_evaluator"


def init_db() -> None:
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.select_db(DB_NAME)
        with conn.cursor() as cur:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB"""
            )
            cur.execute(
                """CREATE TABLE IF NOT EXISTS user_rules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    rule_type VARCHAR(50) NOT NULL DEFAULT 'skin_quality',
                    title VARCHAR(200) DEFAULT '',
                    content MEDIUMTEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_rule (user_id, rule_type)
                ) ENGINE=InnoDB"""
            )
        # Ensure content column is MEDIUMTEXT (migrate from TEXT)
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "ALTER TABLE user_rules MODIFY content MEDIUMTEXT NOT NULL"
                )
            except Exception:
                pass
        logger.info("数据库初始化完成")
    finally:
        conn.close()


def get_connection() -> pymysql.Connection:
    conn = pymysql.connect(**DB_CONFIG, db=DB_NAME)
    return conn


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
