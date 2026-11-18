# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


def test_infer_phase_from_node_name(drill_record):
    assert drill_record.infer_phase("安装MySQL实例") == drill_record.PHASE_APPLY
    assert drill_record.infer_phase("下发MySQL介质包") == drill_record.PHASE_APPLY
    assert drill_record.infer_phase("在目标1.1.1.1添加iptables禁用规则") == drill_record.PHASE_DBHA
    assert drill_record.infer_phase("监测DBHA切换状态") == drill_record.PHASE_DBHA
    assert drill_record.infer_phase("删除演练域名") == drill_record.PHASE_TEARDOWN
    assert drill_record.infer_phase("下发db-actuator介质") == drill_record.PHASE_TEARDOWN
    assert drill_record.infer_phase("卸载mysql实例") == drill_record.PHASE_TEARDOWN
    assert drill_record.infer_phase("机器归还资源池并打标签 drill") == drill_record.PHASE_RETURN_RESOURCE
    assert drill_record.infer_phase("主机转移至资源池空闲模块") == drill_record.PHASE_RETURN_RESOURCE
    assert drill_record.infer_phase("容灾演练 上海 task-1") == ""


def test_locate_node_under_city_subprocess(drill_record):
    task_id = "city-task-1"
    pipeline = {
        "activities": {
            "city-sub": {
                "id": "city-sub",
                "name": "容灾演练 上海 {}".format(task_id),
                "pipeline": {
                    "activities": {
                        "apply-node": {"id": "apply-node", "name": "安装MySQL实例"},
                    }
                },
            }
        }
    }
    assert drill_record.locate_node(pipeline, "apply-node", {task_id}) == (task_id, "安装MySQL实例")
    assert drill_record.locate_node(pipeline, "city-sub", {task_id}) == (
        task_id,
        "容灾演练 上海 {}".format(task_id),
    )
    assert drill_record.locate_node(pipeline, "missing", {task_id}) == (None, "")
