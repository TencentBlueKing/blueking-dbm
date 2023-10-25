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
from xml.etree.ElementTree import Element, SubElement, tostring

from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.bigdata.hdfs import constants
from backend.db_services.bigdata.hdfs.constants import XML_HEADER, XML_LINE_SEPARATOR, XML_TAB_SEPARATOR
from backend.db_services.bigdata.hdfs.query import HDFSListRetrieveResource
from backend.db_services.bigdata.resources import yasg_slz
from backend.db_services.bigdata.resources.views import BigdataResourceViewSet
from backend.db_services.dbbase.resources import serializers
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群列表"),
        query_serializer=serializers.ListResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群详情"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取实例列表"),
        query_serializer=serializers.ListInstancesSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve_instance",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取实例详情"),
        query_serializer=serializers.RetrieveInstancesSerializer(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_table_fields",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取查询返回字段"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceFieldSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_topo_graph",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群拓扑"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceTopoGraphSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
class HDFSClusterViewSetBigdata(BigdataResourceViewSet):
    query_class = HDFSListRetrieveResource
    query_serializer_class = serializers.ListResourceSLZ
    db_type = DBType.Hdfs

    @common_swagger_auto_schema(
        operation_summary=_("获取集群访问xml配置"),
        responses={status.HTTP_200_OK: yasg_slz.XmlResourceSLZ},
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_xmls", serializer_class=None)
    def get_xmls(self, request, bk_biz_id: int, cluster_id: int):
        """
        获取集群访问配置文件信息
        """
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        jn_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_JOURNAL_NODE).values_list(
                "machine__ip", flat=True
            )
        )
        zk_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.HDFS_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )

        resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": str(cluster.immute_domain),
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                "conf_file": cluster.major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP_LEVEL,
            }
        )

        config = resp["content"]
        hdfs_site_dict = config["hdfs-site"]
        core_site_dict = config["core-site"]
        # 生成hdfs-site.xml
        hdfs_site_xml = gen_xml_from_dict(hdfs_site_dict)
        hdfs_site_str = str(tostring(hdfs_site_xml), "utf-8")
        # 渲染配置文件，不太优雅
        hdfs_site_str = (
            hdfs_site_str.replace("{{cluster_name}}", cluster.name)
            .replace("{{nn1_host}}", config["nn1_host"])
            .replace("{{rpc_port}}", config["rpc_port"])
            .replace("{{nn2_host}}", config["nn2_host"])
            .replace("{{http_port}}", config["http_port"])
            .replace("{{jn0_host}}", jn_ips[0])
            .replace("{{jn1_host}}", jn_ips[1])
            .replace("{{jn2_host}}", jn_ips[2])
            .replace("{{zk0_ip}}", zk_ips[0])
            .replace("{{zk1_ip}}", zk_ips[1])
            .replace("{{zk2_ip}}", zk_ips[2])
        )

        hdfs_site_str = f"{XML_HEADER}{hdfs_site_str}"
        # 生成core-site.xml
        core_site_xml = gen_xml_from_dict(core_site_dict)
        core_site_str = str(tostring(core_site_xml), "utf-8")
        # 渲染配置文件
        core_site_str = core_site_str.replace("{{cluster_name}}", cluster.name)

        core_site_str = f"{XML_HEADER}{core_site_str}"

        return Response(
            {
                "cluster_name": cluster.name,
                "domain": cluster.immute_domain,
                "hdfs-site.xml": hdfs_site_str,
                "core-site.xml": core_site_str,
            }
        )


# implemented in Python 3.9 or later
def indent(elem, level=0):
    # 对xml进行格式化，包括换行及缩进
    i = XML_LINE_SEPARATOR + level * XML_TAB_SEPARATOR
    if elem:
        if not elem.text or not elem.text.strip():
            elem.text = i + XML_TAB_SEPARATOR
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def gen_xml_from_dict(config_dict: dict) -> Element:
    xml_element = Element("configuration")
    for key, value in config_dict.items():
        property_xml = SubElement(xml_element, "property")
        name_xml = SubElement(property_xml, "name")
        value_xml = SubElement(property_xml, "value")
        name_xml.text = key
        value_xml.text = value
    indent(xml_element)
    return xml_element
