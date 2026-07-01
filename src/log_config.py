import glob
import logging
import logging.handlers
import os
import re
import time
from datetime import datetime, timedelta


class SizeAndTimeRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Combined time-based + size-based log rotation with total size cleanup."""

    def __init__(self, filename, when='midnight', interval=1, backupCount=7,
                 encoding=None, maxBytes=200 * 1024 * 1024, maxDays=7,
                 maxTotalBytes=2 * 1024 * 1024 * 1024):
        self.maxBytes = maxBytes
        self.maxDays = maxDays
        self.maxTotalBytes = maxTotalBytes
        self.log_dir = os.path.dirname(filename)
        self.base_filename = os.path.basename(filename)
        super().__init__(filename, when=when, interval=interval,
                         backupCount=backupCount, encoding=encoding)

    def shouldRollover(self, record):
        if super().shouldRollover(record):
            return True
        if self.maxBytes and self.stream:
            try:
                self.stream.flush()
                if os.path.getsize(self.baseFilename) >= self.maxBytes:
                    return True
            except OSError:
                pass
        return False

    def doRollover(self):
        super().doRollover()
        self._cleanup()

    def _cleanup(self):
        now = time.time()
        cutoff_days = now - self.maxDays * 86400
        pattern = re.compile(
            re.escape(self.base_filename) + r'(\.\d{4}-\d{2}-\d{2})?(?:\.(\d+))?$'
        )
        log_files = []
        for f in glob.glob(os.path.join(self.log_dir, self.base_filename + '*')):
            m = pattern.match(os.path.basename(f))
            if not m:
                continue
            try:
                stat = os.stat(f)
                log_files.append((f, stat.st_mtime, stat.st_size))
            except OSError:
                continue

        for f, mtime, _ in log_files:
            if mtime < cutoff_days:
                try:
                    os.remove(f)
                except OSError:
                    pass

        total = sum(s for _, _, s in log_files)
        log_files = [(f, m, s) for f, m, s in log_files if os.path.exists(f)]
        log_files.sort(key=lambda x: x[1])
        for f, _, s in log_files:
            if total <= self.maxTotalBytes:
                break
            try:
                os.remove(f)
                total -= s
            except OSError:
                pass

    def emit(self, record):
        try:
            if self.shouldRollover(record):
                self.doRollover()
            super().emit(record)
        except Exception:
            self.handleError(record)


def setup_logging(config):
    log_cfg = config.get('logging', {})
    log_dir = log_cfg.get('log_dir', '/opt/server/logs/ecs/ads')
    log_file = log_cfg.get('log_file', 'gateway.log')
    level = log_cfg.get('level', 'INFO')
    max_bytes = log_cfg.get('max_bytes', 200 * 1024 * 1024)
    max_days = log_cfg.get('max_days', 7)
    max_total_bytes = log_cfg.get('max_total_bytes', 2 * 1024 * 1024 * 1024)
    backup_count = log_cfg.get('backup_count', 7)
    fmt = log_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    file_handler = SizeAndTimeRotatingFileHandler(
        log_path,
        when='midnight',
        interval=1,
        backupCount=backup_count,
        maxBytes=max_bytes,
        maxDays=max_days,
        maxTotalBytes=max_total_bytes,
    )
    file_handler.setFormatter(logging.Formatter(fmt))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)
