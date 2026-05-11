#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import pwd
import sys
from pathlib import Path

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib


def get_log_path():
    sudo_user = os.environ.get("SUDO_USER")

    if sudo_user:
        log_path = Path("/var/log/pardus/pardus-domain-joiner")
    else:
        log_path = Path.home() / ".cache" / "pardus" / "pardus-domain-joiner"

    log_path.mkdir(parents=True, exist_ok=True)

    return log_path


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Block duplicate handler 
    if logger.handlers:
        return

    # ~/./cache/pardus/pardus-domain-joiner/ or /var/log
    logfile = get_log_path() / "pardus-domain-joiner.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # FileHandler (with encoding fallback)
    try:
        file_handler = logging.FileHandler(logfile, encoding="utf-8")
    except TypeError as e:
        print("{} - Logger will be use without utf-8 encoding".format(e))
        file_handler = logging.FileHandler(logfile)

    file_handler.setFormatter(formatter)

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.debug("Logger setup completed.")
    logger.debug("%s is starting.", sys.argv[0])

    return logger
