import logging
import logging.handlers
import queue
import threading
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logs.
    Produces one JSON object per line for easy parsing.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage()
        }

        # Add structured extra fields if present
        extra_fields = ['fan_index', 'temperature', 'speed_percent', 'rpm',
                       'mode', 'register', 'value', 'success', 'duration_ms',
                       'last_speed', 'target_speed', 'new_speed', 'reason']

        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data, ensure_ascii=False)

class DetailedLogger:
    """
    Advanced logging system with:
    - Async queue-based logging (non-blocking)
    - Rotating file handler (10 MB total limit)
    - Structured JSON output
    - Conditional detailed logging (enable via config)
    """
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.log_queue: queue.Queue = queue.Queue(-1)
        self.listener: Optional[logging.handlers.QueueListener] = None

        if not enabled:
            return

        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)

        # Main logger
        self.logger = logging.getLogger('VortECIO.Detailed')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Don't propagate to root logger

        # Queue handler (async)
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.logger.addHandler(queue_handler)

        # File handler with rotation
        # 5 files × 2 MB = 10 MB maximum total
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/fancontrol_detailed.log',
            maxBytes=2*1024*1024,  # 2 MB per file
            backupCount=4,  # Keep 4 backups (total 5 files)
            encoding='utf-8'
        )
        file_handler.setFormatter(StructuredFormatter())

        # Start listener thread
        self.listener = logging.handlers.QueueListener(
            self.log_queue,
            file_handler,
            respect_handler_level=True
        )
        self.listener.start()

        # Log initialization
        self.logger.info('detailed_logging_started', extra={
            'version': '1.0.0',
            'max_size_mb': 10
        })

    def log_fan_state(self, fan_index: int, temp: Optional[float],
                      speed: int, rpm: int, mode: str):
        """Log current fan state"""
        if not self.enabled:
            return

        self.logger.debug('fan_state', extra={
            'fan_index': fan_index,
            'temperature': temp,
            'speed_percent': speed,
            'rpm': rpm,
            'mode': mode
        })

    def log_ec_operation(self, operation: str, register: int,
                         value: int, success: bool):
        """Log EC read/write operation"""
        if not self.enabled:
            return

        self.logger.debug(f'ec_{operation}', extra={
            'register': f'0x{register:02X}',
            'value': value,
            'success': success
        })

    def log_hysteresis_decision(self, fan_index: int, temp: Optional[float],
                                last_speed: int, target_speed: int,
                                new_speed: int, reason: str):
        """Log hysteresis algorithm decision"""
        if not self.enabled:
            return

        self.logger.debug('hysteresis_decision', extra={
            'fan_index': fan_index,
            'temperature': temp,
            'last_speed': last_speed,
            'target_speed': target_speed,
            'new_speed': new_speed,
            'reason': reason
        })

    def log_performance(self, operation: str, duration_ms: float):
        """Log performance metrics"""
        if not self.enabled:
            return

        # Warn if operation takes too long
        level = logging.WARNING if duration_ms > 100 else logging.DEBUG
        self.logger.log(level, f'performance_{operation}', extra={
            'duration_ms': round(duration_ms, 2)
        })

    def log_sensor_read(self, sensor_type: str, cpu_temp: Optional[float],
                        gpu_temp: Optional[float], success: bool):
        """Log temperature sensor reading"""
        if not self.enabled:
            return

        self.logger.debug('sensor_read', extra={
            'sensor_type': sensor_type,
            'cpu_temp': cpu_temp,
            'gpu_temp': gpu_temp,
            'success': success
        })

    def log_config_loaded(self, model: str, fans: int, critical_temp: float):
        """Log configuration load event"""
        if not self.enabled:
            return

        self.logger.info('config_loaded', extra={
            'model': model,
            'fan_count': fans,
            'critical_temp': critical_temp
        })

    def shutdown(self):
        """Clean shutdown of logging system"""
        if self.enabled and self.listener:
            self.logger.info('detailed_logging_stopped')
            self.listener.stop()

# Global instance (initialized in main.py)
detailed_logger: Optional[DetailedLogger] = None

def init_detailed_logging(enabled: bool):
    """Initialize detailed logging system"""
    global detailed_logger
    detailed_logger = DetailedLogger(enabled=enabled)

def get_detailed_logger() -> Optional[DetailedLogger]:
    """Get the global detailed logger instance"""
    return detailed_logger
