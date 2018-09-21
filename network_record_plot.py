#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plots data collected by network record script."""

from matplotlib import pyplot as plt
from sqlite3 import connect

CONDITION = ("WHERE date <> \"2018-02-11\" AND download_main <> 0 AND "
             "ping_main < 1000")
BASE_DIR = "/home/thomas/Drive/tbagrel/accounts/network/network_record/"
DATABASE_PATH = BASE_DIR + "network_record.db"
TABLE_NAME = "records"

def avg(data):
    """Returns the average of the specified iterable."""
    return sum(data) / len(data)

def print_stats(data, name):
    """Prints min, max and average of the specified iterable."""
    print("### {} ###".format(name.upper()))
    print("min_{}: {}".format(name, min(data)))
    print("max_{}: {}".format(name, max(data)))
    print("avg_{}: {}".format(name, avg(data)))
    print("\n")

def main():
    """Main function."""
    connection = connect(DATABASE_PATH, timeout=10)
    cursor = connection.cursor()
    raw_rows = cursor.execute(
        "SELECT * from {} {}".format(TABLE_NAME, CONDITION))
    rows = [
        {
            "date": row[0],
            "hour": row[1],
            "name_main": row[2],
            "ping_main": row[3],
            "download_main": row[4],
            "upload_main": row[5],
            "backup_name": row[6],
            "ping_backup": row[7],
            "download_backup": row[8],
            "upload_backup": row[9]
        }
        for row in raw_rows
    ]
    X = ["{} {}".format(row["date"], row["hour"]) for row in rows]
    Y_1 = [row["ping_main"] for row in rows]
    Y_2 = [row["download_main"] for row in rows]
    Y_3 = [row["upload_main"] for row in rows]
    print_stats(Y_1, "ping")
    print_stats(Y_2, "download")
    print_stats(Y_3, "upload")
    fig, axis_1 = plt.subplots()
    axis_2 = axis_1.twinx()
    axis_3 = axis_2.twinx()
    axis_1.plot(X, Y_1, color="r")
    for t in axis_1.get_yticklabels(): t.set_color("r")
    axis_2.plot(X, Y_2, color="b")
    for t in axis_2.get_yticklabels(): t.set_color("b")
    axis_3.plot(X, Y_3, color="g")
    for t in axis_3.get_yticklabels(): t.set_color("g")
    plt.xticks(range(1, len(X) // (4 * 24) + 1))
    plt.savefig("data_gathered.png", dpi=300)
    plt.show()
    connection.close()
    return 0

if __name__ == "__main__":
    main()
