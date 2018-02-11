#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests network speed each DELAY seconds and uploads results on the
specified database."""

import subprocess
import datetime
import sqlite3
import time
import json

DEBUG_LEVEL = 3
FANCY_LEVEL = {
    0: "E",
    1: "W",
    2: "I",
    3: "L",
}

DATE_FORMAT = "%Y-%m-%d"
HOUR_FORMAT = "%H:%M:%S"

FAILED_REAL = 0
FAILED_TEXT = "0"
NOT_MEASURED_REAL = -1
NOT_MEASURED_TEXT = "-1"

TABLE_FORMAT = {
    "date": "TEXT",
    "hour": "TEXT",
    "main_name": "TEXT",
    "ping_main": "REAL",
    "download_main": "REAL",
    "upload_main": "REAL",
    "backup_name": "TEXT",
    "ping_backup": "REAL",
    "download_backup": "REAL",
    "upload_backup": "REAL"
}
PRIMARY_KEY = "(date, hour)"
TABLE_NAME = "records"

MAIN_SERVER = 13661  # Vialis, Woippy
BACKUP_SERVER = 4997  # inexio, Saarlouis
TIMEOUT = 10  # Timeout time in seconds
DELAY = 10 * 60  # Delay between two measures in seconds
DOWNLOAD_JSON_FIELD = "download"
UPLOAD_JSON_FIELD = "upload"
PING_JSON_FIELD = "ping"
NAME_JSON_FIELD = "name"
DATABASE_PATH = "./network_records.db"
START_STOP_PATH = "./record_start_stop"
START_STATE = "start"
STOP_STATE = "stop"
ENC = "utf-8"

CMD = ["speedtest-cli", "--json", "--server", "", "--timeout", TIMEOUT]
SERVER_POSITION = 3

def print_debug(level, msg):
    """Prints msg iif DEBUG_LEVEL >= level"""
    if DEBUG_LEVEL >= level:
        print("[{}] {}".format(FANCY_LEVEL[level], msg))

def database_connect():
    """Returns database object if possible."""
    try:
        connection = sqlite3.connect(DATABASE_PATH, timeout=TIMEOUT)
        return connection
    except Exception as e:
        print_debug(0, "Unable to connect database: <{}>".format(e))
        return None

def create_network_records_table():
    """Creates for the first time the record table."""
    connection = database_connect()
    if connection is None:
        return -1
    c = connection.cursor()
    fields = ", ".join(["{} {}".format(f, t) for (f, t) in TABLE_FORMAT])
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
    now = datetime.now()
    date = now.strftime(DATE_FORMAT)
    hour = now.strftime(HOUR_FORMAT)
    CMD[SERVER_POSITION] = MAIN_SERVER
    result = subprocess.check_output(
        CMD, stderr=subprocess.STDOUT).decode(ENC)
    try:
        json_results = json.loads(result)
        name_main = json_results[NAME_JSON_FIELD]
        ping_main = json_results[PING_JSON_FIELD]
        download_main = json_results[DOWNLOAD_JSON_FIELD]
        upload_main = json_results[UPLOAD_JSON_FIELD]
        name_backup = NOT_MEASURED_TEXT
        ping_backup = NOT_MEASURED_REAL
        download_backup = NOT_MEASURED_REAL
        upload_backup = NOT_MEASURED_REAL
    except Exception as e:
        print_debug(
            1, "Unable to get results from main server: <{}>".format(e))
        name_main = FAILED_TEXT
        ping_main = FAILED_REAL
        download_main = FAILED_REAL
        upload_main = FAILED_REAL
        CMD[SERVER_POSITION] = BACKUP_SERVER
        result = subprocess.check_output(
            CMD, stderr=subprocess.STDOUT).decode(ENC)
        try:
            json_results = json.loads(result)
            name_backup = json_results[NAME_JSON_FIELD]
            ping_backup = json_results[PING_JSON_FIELD]
            download_backup = json_results[DOWNLOAD_JSON_FIELD]
            upload_backup = json_results[UPLOAD_JSON_FIELD]
        except Exception as e:
            print_debug(
                1, "Unable to get results from backup server: <{}>".format(e))
            name_backup = FAILED_TEXT
            ping_backup = FAILED_REAL
            download_backup = FAILED_REAL
            upload_backup = FAILED_REAL
    record = (
        date, hour, name_main, ping_main, download_main, upload_main,
        name_backup, ping_backup, download_backup, upload_backup)
    print_debug(3, "New record: <{}>".format(record))
    c = connection.cursor()
    try:
        insert_query = ""  # TODO: write query
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
    stop = False
    with open(START_STOP_PATH, "w", encoding=ENC) as start_stop_file:
        start_stop_file.write(START_STATE)
    while not stop:
        r = test_network(connection)
        if r != 0:
            return 2
        time.sleep(DELAY)
        # get running state
        try:
            with open(START_STOP_PATH, "r", encoding=ENC) as start_stop_file:
                state = start_stop_file.read().strip().lower()
            if state != START_STATE:
                stop = True
        except Exception as e:
            print_debug(
                0, "Unable to get running state: <{}>".format(e))
            return 1
    with open(START_STOP_PATH, "w", encoding=ENC) as start_stop_file:
        start_stop_file.write(STOP_STATE)
    return 0

if __name__ == "__main__":
    main()
