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
import os

import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Pipelines(Base):
    __tablename__ = 'pipelines'
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String)
    namespace = sqla.Column(sqla.String)
    sqla.UniqueConstraint('name', 'namespace')


class Pipelineruns(Base):
    __tablename__ = 'pipelineruns'
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    namespace = sqla.Column(sqla.String, nullable=False)
    start_time = sqla.Column(sqla.DateTime(), nullable=False)
    completion_time = sqla.Column(sqla.DateTime(), nullable=True)
    status = sqla.Column(sqla.SmallInteger(), nullable=False)
    json = sqla.Column(sqla.Text(), nullable=False)
    pipeline_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey('pipelines.id'), nullable=False)
    sqla.UniqueConstraint('name', 'namespace', 'start_time')


class Taskruns(Base):
    __tablename__ = 'taskruns'
    __existence__ = ("name", "namespace", "start_time")
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    namespace = sqla.Column(sqla.String, nullable=False)
    start_time = sqla.Column(sqla.DateTime(), nullable=False)
    completion_time = sqla.Column(sqla.DateTime(), nullable=True)
    status = sqla.Column(sqla.SmallInteger(), nullable=False)
    pod_name = sqla.Column(sqla.String, nullable=False)
    json = sqla.Column(sqla.Text(), nullable=False)
    pipelinerun_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey('pipelineruns.id'), nullable=False)
    sqla.UniqueConstraint('name', 'namespace', 'start_time')


class Steps(Base):
    __tablename__ = "steps"
    __existence__ = ("name", "namespace", "taskrun_id")
    id = sqla.Column(sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    namespace = sqla.Column(sqla.String, nullable=False)
    taskrun_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey('taskruns.id'), nullable=False)
    log = sqla.Column(sqla.Text)


def get_or_create(session, model, **kwargs):
    if hasattr(model, '__existence__'):
        filter_by = {x: kwargs[x] for x in kwargs if x in model.__existence__}
    else:
        filter_by = kwargs
    instance = session.query(model).filter_by(**filter_by).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


def start_engine(database_file):
    engine = sqla.create_engine(
        'sqlite:////' + database_file, echo="SQL_DEBUG" in os.environ)

    session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return (engine, session)
