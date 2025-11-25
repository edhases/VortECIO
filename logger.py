"""
Централізована система логування для FanControl
"""
import logging
import os
from datetime import datetime

def setup_logger():
    """Налаштування логера з файлом та консоллю"""

    # Створити папку для логів
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Файл логу з датою
    log_file = os.path.join(log_dir, f"fancontrol_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    # Формат логу
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Налаштування root logger
    logging.basicConfig(
        level=logging.DEBUG,  # Все логувати
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Файл (DEBUG рівень - все)
            logging.FileHandler(log_file, encoding='utf-8'),
            # Консоль (INFO рівень - важливе)
            logging.StreamHandler()
        ]
    )

    # Налаштувати рівень для консолі окремо
    console_handler = logging.getLogger().handlers[1]
    console_handler.setLevel(logging.INFO)

    # Повернути logger
    logger = logging.getLogger('FanControl')
    logger.info(f"=== FanControl Started ===")
    logger.info(f"Log file: {log_file}")

    return logger

def get_logger(name):
    """Отримати logger для модуля"""
    return logging.getLogger(f'FanControl.{name}')
