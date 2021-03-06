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

import sqlalchemy as sqla
from sqlalchemy.orm import sessionmaker

import db


def test():
    engine = sqla.create_engine('sqlite:////tmp/test.db')
    db.Base.metadata.drop_all(engine)
    db.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    pipelineRunName = 'pipeline-randomwords-run-vxw5w'
    pipelineName = 'pipeline-randomwords'
    taskRunName = 'step-bacon'
    namespace = 'play'

    p = db.get_or_create(
        session, db.Pipelines, name=pipelineName, namespace=namespace)
    p2 = db.get_or_create(
        session, db.Pipelines, name="pipeline2", namespace=namespace)
    p3 = db.get_or_create(
        session, db.Pipelines, name="pipeline3", namespace=namespace)

    pr = db.get_or_create(
        session,
        db.Pipelineruns,
        name=pipelineRunName,
        namespace=namespace,
        start_time=datetime.datetime.now(),
        completion_time=datetime.datetime.now(),
        status=0,
        pipeline_id=p.id,
        json='{}')
    db.get_or_create(
        session,
        db.Pipelineruns,
        name="pr2",
        namespace=namespace,
        start_time=datetime.datetime.now(),
        completion_time=datetime.datetime.now(),
        status=0,
        pipeline_id=p2.id,
        json='{}')
    db.get_or_create(
        session,
        db.Pipelineruns,
        name="pipeline3",
        namespace=namespace,
        start_time=datetime.datetime.now(),
        completion_time=datetime.datetime.now(),
        status=0,
        pipeline_id=p3.id,
        json='{}')
    db.get_or_create(
        session,
        db.Pipelineruns,
        name="pipeline4",
        namespace=namespace,
        start_time=datetime.datetime.now(),
        completion_time=datetime.datetime.now(),
        status=0,
        pipeline_id=p.id,
        json='{}')
    # last one refer to first id created
    res = session.query(db.Pipelineruns, db.Pipelines).join(db.Pipelines).all()
    assert (res[-1][1].id == 1)

    tr1 = db.get_or_create(
        session,
        db.Taskruns,
        name=taskRunName,
        namespace=namespace,
        start_time=datetime.datetime.now(),
        completion_time=datetime.datetime.now(),
        pod_name="pod1",
        status=0,
        json='{}',
        pipelinerun_id=pr.id,
    )

    start_time2 = datetime.datetime.now()
    completion_time2 = datetime.datetime.now()
    tr2 = db.get_or_create(
        session,
        db.Taskruns,
        name=taskRunName,
        namespace=namespace,
        start_time=start_time2,
        completion_time=completion_time2,
        pod_name="pod1",
        status=0,
        json='{}',
        pipelinerun_id=pr.id,
    )

    assert (tr1.id != tr2.id)

    tr3 = db.get_or_create(
        session,
        db.Taskruns,
        name=taskRunName,
        namespace=namespace,
        start_time=start_time2,
        completion_time=datetime.datetime.now(),
        pod_name="pod2",
        status=0,
        json='{}',
        pipelinerun_id=pr.id,
    )
    assert (tr3.id == tr2.id)

    tr2 = db.get_or_create(
        session,
        db.Taskruns,
        name=taskRunName,
        namespace=namespace,
        start_time=start_time2,
        completion_time=completion_time2,
        pod_name="pod1",
        status=0,
        json='{}',
        pipelinerun_id=pr.id,
    )

    s1 = db.get_or_create(
        session,
        db.Steps,
        name="step1",
        namespace=namespace,
        taskrun_id=tr1.id,
        log="FOO BAR",
    )
    s1c = db.get_or_create(
        session,
        db.Steps,
        name="step1",
        namespace=namespace,
        taskrun_id=tr1.id,
        log="FOO BAR",
    )
    assert (s1.id == s1c.id)

    res = session.query(
        db.Pipelineruns).filter(db.Pipelineruns.name == 'pipeline4').first()
    assert (res.name == 'pipeline4')


if __name__ == '__main__':
    test()
