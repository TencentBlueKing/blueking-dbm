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
import base64
import logging
import re
from enum import Enum
from typing import List

import requests
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.test import Client
from django.utils.translation import ugettext_lazy as _
from jinja2 import Environment
from rest_framework import serializers
from rest_framework.response import Response

from backend import env
from backend.components import CCApi, GcsDnsApi, JobApi
from backend.db_meta.api import common
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.flow.views.base import FlowTestView

client = Client()
logger = logging.getLogger("root")


class ScriptTypeEnum(Enum):
    Bash = 1
    Python = 2
    Perl = 3


class RollbackPipelineApiView(FlowTestView):
    def post(self, request):
        serializer = RollbackPipelineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(f"failed: {serializer.errors}")
        root_id = request.data["root_id"]
        cluster_type = request.data["cluster_type"]
        engine = BambooEngine(root_id=root_id)
        exists = FlowTree.objects.filter(root_id=root_id).exists()
        if not exists:
            return Response("success")
        metas_data = []
        nodes = FlowNode.objects.filter(root_id=root_id)
        for node in nodes:
            data = engine.get_execution_data(node.node_id).data
            try:
                node_name = data["inputs"]["kwargs"]["node_name"]
                if re.match(r"TenDB", node_name):
                    metas_data.append(data)
            except Exception:
                clean_hosts(20000, 10000, [])
        for meta in metas_data:
            kwargs = meta["inputs"]["kwargs"]
            logger.info(f"kwargs: {kwargs}")
            cluster_info = kwargs["cluster"]
            bk_biz_id = cluster_info["bk_biz_id"]
            bk_cloud_id = cluster_info["bk_cloud_id"]
            domain_names = [{"domain_name": cluster_info["immute_domain"]}]
            if cluster_info.get("slave_domain"):
                domain_names.append({"domain_name": cluster_info["slave_domain"]})
            name = cluster_info["name"]
            script_hosts = []
            hosts = []
            proxies = []
            storages = []
            mysql_port = 20000
            proxy_port = 10000
            for host in kwargs["machines"]:
                hosts.append(host["ip"])
                script_hosts.append({"ip": host["ip"], "bk_cloud_id": 0})
                if host["machine_type"] == "proxy":
                    proxy_port = cluster_info["proxies"][0]["port"]
                    proxies.append({"ip": host["ip"], "port": proxy_port})
                else:
                    try:
                        mysql_port = cluster_info["storages"][0]["port"]
                        storages.append({"ip": host["ip"], "port": mysql_port})
                    except KeyError:
                        mysql_port = cluster_info["storage"]["port"]
                        storages.append(cluster_info["storage"])
            # clean hosts
            clean_hosts(mysql_port, proxy_port, script_hosts)
            # delete ClusterEntry
            try:
                cluster = Cluster.objects.filter(name=name, bk_biz_id=bk_biz_id, cluster_type=cluster_type)
                ClusterEntry.objects.filter(cluster__in=cluster).delete()
            except Cluster.DoesNotExist:
                logger.warning("not found cluster")
                pass
            # delete Cluster
            Cluster.objects.filter(name=name, bk_biz_id=bk_biz_id, cluster_type=cluster_type).delete()
            # delete ProxyInstance
            proxy_objs = common.filter_out_instance_obj(proxies, ProxyInstance.objects.all())
            proxy_objs.delete()
            # delete StorageInstance
            storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
            storage_objs.delete()
            # delete Machine
            Machine.objects.filter(ip__in=hosts).delete()
            # 删除DNS记录
            resp = CCApi.search_business(
                {
                    "fields": ["bk_biz_id", "bk_biz_name", "db_app_abbr"],
                    "biz_property_filter": {
                        "condition": "AND",
                        "rules": [{"field": "bk_biz_id", "operator": "equal", "value": int(bk_biz_id)}],
                    },
                    "page": {"start": 0, "limit": 10, "sort": ""},
                },
                raw=True,
                use_admin=True,
            )
            logger.info(f"business response: {resp}")
            try:
                app = resp["data"]["info"][0]["db_app_abbr"]
                logger.info(f"appname: {app}")
                resp = GcsDnsApi.delete_domain({"app": app, "domains": domain_names, "bk_cloud_id": bk_cloud_id})
                logger.info(f"delete domains response: {resp}")
            except IndexError or KeyError:
                logger.warning(f"not found app with bk_biz_id: {bk_biz_id}")
            # 回收主机到空闲模块
            bk_host_ids = []
            for storage in storage_objs:
                m = storage.machine
                bk_host_ids.append(m.bk_host_id)
            for proxy in proxy_objs:
                m = proxy.machine
                bk_host_ids.append(m.bk_host_id)
            logger.info(f"ready transfer host to idle module with hosts: {bk_host_ids}")
            if len(bk_host_ids) > 0:
                resp = CCApi.transfer_host_to_idlemodule(
                    {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": bk_host_ids}
                )
                logger.info(f"transfer_host_to_idlemodule response: {resp}")
            # 重新导入主机至资源池
            url = ""
            resp = requests.post(url=url, json={"apply_for": "", "ips": hosts, "labels": {}})
            if resp.status_code >= 400:
                return Response(_("导入资源池失败"))
        return Response("success")


def clean_hosts(mysql_port: int, proxy_port: int, hosts: List):
    jinja_env = Environment()
    template = jinja_env.from_string("")
    script_plain = template.render({"mysql_port": mysql_port, "proxy_port": proxy_port})
    body = {
        "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
        "script_content": str(base64.b64encode(script_plain.encode("utf-8")), "utf-8"),
        "task_name": "rollback_pipeline",
        "account_alias": "root",
        "script_language": ScriptTypeEnum.Bash.value,
        "target_server": {"ip_list": hosts},
    }
    JobApi.fast_execute_script(body, raw=True, use_admin=True)


class RollbackPipelineClusterTypeEnum(StructuredEnum):
    TenDBHA = EnumField("tendbha", _("高可用架构"))
    TenDBSingle = EnumField("tendbsingle", _("单实例架构"))


class RollbackPipelineSerializer(serializers.Serializer):
    root_id = serializers.CharField(required=True)
    cluster_type = serializers.ChoiceField(required=True, choices=RollbackPipelineClusterTypeEnum.get_choices())


class PipelineTreeApiView(FlowTestView):
    def get(self, request, root_id):
        engine = BambooEngine(root_id=root_id)
        tree = engine.get_pipeline_tree_states()
        return Response(tree)
