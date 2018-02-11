#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests network speed each DELAY seconds and uploads results on the
specified database."""

import datetime
import json
import sqlite3
import subprocess
import time

OP_MODE = False

DEBUG_LEVEL = 2
FANCY_LEVEL = {
    0: "E",
    1: "W",
    2: "I",
    3: "L",
    4: "D",
}

DATE_FORMAT = "%Y-%m-%d"
HOUR_FORMAT = "%H:%M:%S"

FAILED_REAL = 0
FAILED_TEXT = "0"
NOT_MEASURED_REAL = -1
NOT_MEASURED_TEXT = "-1"

TABLE_FORMAT = (
    ("date", "TEXT"),
    ("hour", "TEXT"),
    ("main_name", "TEXT")
    ("ping_main", "REAL")
    ("download_main", "REAL")
    ("upload_main", "REAL")
    ("backup_name", "TEXT")
    ("ping_backup", "REAL")
    ("download_backup", "REAL")
    ("upload_backup", "REAL")
)
PRIMARY_KEY = "(date, hour)"
TABLE_NAME = "records"

BASE_DIR = "/home/pi/network_record/"
MAIN_SERVER = 13661  # Vialis, Woippy
NAME_MAIN = "Vialis, Woopy"
BACKUP_SERVER = 4997  # inexio, Saarlouis
NAME_BACKUP = "inexio, Saarlouis"
TIMEOUT = 10  # Timeout time in seconds
DELAY = 15 * 60  # Delay between two measures in seconds
# DELAY = 30  # Delay between two measures in seconds
DOWNLOAD_JSON_FIELD = "download"
UPLOAD_JSON_FIELD = "upload"
PING_JSON_FIELD = "ping"
DATABASE_PATH = BASE_DIR + "network_record.db"
START_STOP_PATH = BASE_DIR + "network_record_start_stop"
LOG_PATH = BASE_DIR + "network_record.log"
START_STATE = "start"
STOP_STATE = "stop"
ENC = "utf-8"

CMD = ["speedtest-cli", "--json", "--server", "", "--timeout", str(TIMEOUT)]
SERVER_POSITION = 3
CLEAR_CMD = ["rm", ""]
PATH_POSITION = 1


def print_debug(level, msg, in_log_file=True):
    """Prints msg iif DEBUG_LEVEL >= level"""
    if DEBUG_LEVEL >= level:
        fancy_msg = "[{}] {}".format(FANCY_LEVEL[level], msg)
        print(fancy_msg)
        if in_log_file:
            with open(LOG_PATH, "a", encoding=ENC) as log_file:
                log_file.write("{}\n".format(fancy_msg))


def database_connect():
    """Returns database object if possible."""
    try:
        connection = sqlite3.connect(DATABASE_PATH, timeout=TIMEOUT)
        return connection
    except Exception as e:
        print_debug(0, "Unable to connect database: <{}>".format(e))
        return None


def clean():
    """Completely REMOVES previous database files."""
    r = 0
    try:
        CLEAR_CMD[PATH_POSITION] = START_STOP_PATH
        subprocess.check_call(CLEAR_CMD)
        print_debug(2, "Start stop file successfully removed", False)
    except Exception as e:
        r = r << 1 + 1
        print_debug(1, "Unable to remove start stop file: <{}>".format(e),
                    False)
    try:
        CLEAR_CMD[PATH_POSITION] = LOG_PATH
        subprocess.check_call(CLEAR_CMD)
        print_debug(2, "Log file successfully removed", False)
    except Exception as e:
        r = r << 1 + 1
        print_debug(1, "Unable to remove Log file: <{}>".format(e), False)
    try:
        CLEAR_CMD[PATH_POSITION] = DATABASE_PATH
        subprocess.check_call(CLEAR_CMD)
        print_debug(2, "Database file successfully removed", False)
    except Exception as e:
        r = r << 1 + 1
        print_debug(1, "Unable to remove database file: <{}>".format(e), False)
    return r


def create_table():
    """Creates for the first time the record table."""
    connection = database_connect()
    if connection is None:
        return -1
    c = connection.cursor()
    fields = ", ".join(["{} {}".format(f, t)
                        for (f, t) in TABLE_FORMAT])
    create_query = ("CREATE TABLE IF NOT EXISTS {} ({}, PRIMARY KEY {})"
        .format(TABLE_NAME, fields, PRIMARY_KEY))
    try:
        c.execute(create_query)
        connection.commit()
    except Exception as e:
        print_debug(0, "Unable to create table: <{}>".format(e))
        return -1
    finally:
        connection.close()
    print_debug(2, "Table successfully created!")
    return 0


def test_network(connection):
    """Tests internet connection."""
    now = datetime.datetime.now()
    date = now.strftime(DATE_FORMAT)
    hour = now.strftime(HOUR_FORMAT)
    CMD[SERVER_POSITION] = str(MAIN_SERVER)
    try:
        result = subprocess.check_output(
            CMD, stderr=subprocess.STDOUT).decode(ENC)
        print_debug(4, "Main result: {}".format(result))
        json_results = json.loads(result)
        ping_main = json_results[PING_JSON_FIELD]
        download_main = json_results[DOWNLOAD_JSON_FIELD]
        upload_main = json_results[UPLOAD_JSON_FIELD]
        ping_backup = NOT_MEASURED_REAL
        download_backup = NOT_MEASURED_REAL
        upload_backup = NOT_MEASURED_REAL
    except Exception as e:
        print_debug(
            1, "Unable to get results from main server: <{}>".format(e))
        ping_main = FAILED_REAL
        download_main = FAILED_REAL
        upload_main = FAILED_REAL
        CMD[SERVER_POSITION] = str(BACKUP_SERVER)
        try:
            result = subprocess.check_output(
                CMD, stderr=subprocess.STDOUT).decode(ENC)
            print_debug(4, "Backup result: {}".format(result))
            json_results = json.loads(result)
            ping_backup = json_results[PING_JSON_FIELD]
            download_backup = json_results[DOWNLOAD_JSON_FIELD]
            upload_backup = json_results[UPLOAD_JSON_FIELD]
        except Exception as e:
            print_debug(
                1, "Unable to get results from backup server: <{}>".format(e))
            ping_backup = FAILED_REAL
            download_backup = FAILED_REAL
            upload_backup = FAILED_REAL
    record = (
        date, hour, NAME_MAIN, ping_main, download_main, upload_main,
        NAME_BACKUP, ping_backup, download_backup, upload_backup)
    print_debug(3, "New record: <{}>".format(record))
    c = connection.cursor()
    try:
        insert_query = "INSERT INTO {} VALUES {}".format(TABLE_NAME, record)
        c.execute(insert_query)
        connection.commit()
    except Exception as e:
        print_debug(0, "Unable to commit new record: <{}>".format(e))
        return -1
    return 0


def main():
    """Main function."""
    connection = database_connect()
    if connection is None:
        return -1
    print_debug(2, "Connection to the database established!")
    stop = False
    with open(START_STOP_PATH, "w", encoding=ENC) as start_stop_file:
        start_stop_file.write(START_STATE)
    try:
        while not stop:
            r = test_network(connection)
            if r != 0:
                return 2
            time.sleep(DELAY)
            try:
                with open(START_STOP_PATH, "r", encoding=ENC) as \
                        start_stop_file:
                    state = start_stop_file.read().strip().lower()
                if state != START_STATE:
                    print_debug(
                        2, "Stopping loop (start stop file-triggered)")
                    stop = True
            except Exception as e:
                print_debug(
                    0, "Unable to get running state: <{}>".format(e))
                with open(START_STOP_PATH, "w", encoding=ENC) as \
                        start_stop_file:
                    start_stop_file.write(STOP_STATE)
                connection.close()
                print_debug(2, "Connection to the database closed.")
                return 1
    except KeyboardInterrupt:
        print_debug(
            2, "Stopping loop (keyboard interrupt-triggered)")
    finally:
        with open(START_STOP_PATH, "w", encoding=ENC) as start_stop_file:
            start_stop_file.write(STOP_STATE)
        connection.close()
        print_debug(2, "Connection to the database closed.")
    return 0


if __name__ == "__main__":
    if OP_MODE:
        import sys

        n = len(sys.argv)
        if n == 1 or (n == 2 and sys.argv[1].strip().lower() == "run"):
            main()
        elif n == 2 and sys.argv[1].strip().lower() == "create":
            create_table()
        elif n == 2 and sys.argv[1].strip().lower() == "clean":
            clean()
        else:
            print(
                "[LAUNCHER] Invalid use of the script:\n"
                "    network_record.py [run (default) | create | clean]")
    else:
        main()
