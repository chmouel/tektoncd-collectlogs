# -*- coding: utf-8 -*-
# Author: Chmouel Boudjnah <chmouel@chmouel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
import os
import sqlite3


def create_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pipeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name text not null,
        namespace text not null,
        UNIQUE(namespace, name)
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PipelineRun (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name text not null,
        namespace text not null,
        start_time text not null,
        status integers(1) not null,
        completion_time text not null,
        pipelineID int not null,
        json text not null,
        UNIQUE(namespace, name, start_time)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TaskRun (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name varchar(255) not null,
        namespace text not null,
        start_time text not null,
        completion_time text not null,
        status integers(1) not null,
        podname text not null,
        json text,
        pipelineRunID int not null,
        UNIQUE(namespace, name, pipelineRunID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Steps (
       id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name varchar(255) not null,
        namespace text not null,
        taskRunId int not null,
        log blob,
        UNIQUE(namespace, name, taskRunId)
    )
    """)


def insert_if_not_exists(cursor, otype, existence={}, **kwargs):
    """Will insert a bunch of fields in a table {otype} if existence fields
    don't duplicate already"""
    if not existence:
        existence = kwargs.keys()
    query = f" SELECT id FROM {otype} WHERE "
    query += " AND ".join(
        [f"{x}='{kwargs[x]}'" for x in kwargs if x in existence])
    # print("SELECT QUERY: " + query)
    existID = cursor.execute(query).fetchone()
    if existID:
        return existID[0]

    query = f"insert into {otype} ({', '.join(list(kwargs.keys()))}) VALUES("
    query += ", ".join([f"'{x}'" for x in kwargs.values()])
    query += ")"
    print("INSERT QUERY: " + query)
    return cursor.execute(query).lastrowid


def test():
    os.remove("/tmp/test.db")
    conn = sqlite3.connect("/tmp/test.db")
    create_table(conn)
    cursor = conn.cursor()

    namespace = 'play'
    pipelineName = 'pipeline-randomwords'
    pipelineRunName = 'pipeline-randomwords-run-vxw5w'
    taskRunName = 'pipeline-randomwords-run-vxw5w-baconipsum-1-skgdx'

    insert_if_not_exists(
        cursor, "Pipeline", name=pipelineName, namespace=namespace)
    pipelineID = cursor.lastrowid

    insert_if_not_exists(
        cursor,
        "PipelineRun",
        name=pipelineRunName,
        namespace=namespace,
        start_time=str(datetime.datetime.now()),
        completion_time=str(datetime.datetime.now()),
        status=0,
        pipelineID=pipelineID,
        json='{}')
    pipelineRunID = cursor.lastrowid

    taskRunId = insert_if_not_exists(
        cursor,
        "TaskRun",
        existence=("name", "namespace"),
        podname="pod1",
        namespace=namespace,
        name=taskRunName,
        start_time=str(datetime.datetime.now()),
        completion_time=str(datetime.datetime.now()),
        status=0,
        pipelineRunID=pipelineRunID,
        json='{}')

    # SECOND TIME should be different since different start_time
    start_time2 = str(datetime.datetime.now())
    taskRunId2 = insert_if_not_exists(
        cursor,
        "TaskRun",
        existence=("name", "namespace", "start_time"),
        namespace=namespace,
        name=taskRunName,
        podname="pod2",
        start_time=start_time2,
        completion_time=str(datetime.datetime.now()),
        status=0,
        pipelineRunID=pipelineRunID,
        json='{}')
    assert (taskRunId != taskRunId2)

    # Third time same ID since same start_time, name, namespace
    taskRunId3 = insert_if_not_exists(
        cursor,
        "TaskRun",
        existence=("name", "namespace", "start_time"),
        namespace=namespace,
        podname="pod2",
        name=taskRunName,
        start_time=start_time2,
        completion_time=str(datetime.datetime.now()),
        status=0,
        pipelineRunID=pipelineRunID,
        json='{}')
    assert (taskRunId2 == taskRunId3)
    conn.commit()
    conn.close()


if __name__ == '__main__':
    test()
