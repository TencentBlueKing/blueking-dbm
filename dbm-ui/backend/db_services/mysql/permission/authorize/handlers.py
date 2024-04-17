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
import copy
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Union

from django.conf import settings
from django.core.cache import cache
from django.http.response import HttpResponse
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components.gcs.client import GcsApi
from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.components.scr.client import ScrApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.mysql.permission.authorize.dataclass import (
    AuthorizeMeta,
    ExcelAuthorizeMeta,
    HostInAuthorizeFilterMeta,
)
from backend.db_services.mysql.permission.authorize.models import MySQLAuthorizeRecord
from backend.db_services.mysql.permission.constants import AUTHORIZE_DATA_EXPIRE_TIME, AUTHORIZE_EXCEL_ERROR_TEMPLATE
from backend.db_services.mysql.permission.exceptions import DBPermissionBaseException
from backend.exceptions import ApiResultError
from backend.ticket.builders.mysql.mysql_authorize_rules import MySQLAuthorizeRulesSerializer
from backend.ticket.constants import TicketStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.cache import data_cache
from backend.utils.excel import ExcelHandler


class AuthorizeHandler(object):
    """
    封装授权相关的处理操作
    """

    def __init__(self, bk_biz_id: int, operator: str = None):
        """
        :param bk_biz_id: 业务ID
        :param operator: 操作者
        """

        self.bk_biz_id = bk_biz_id
        self.operator = operator

    def pre_check_rules(self, authorize: AuthorizeMeta, task_index: int = None) -> Dict:
        """
        - 清洗规则数据
        :param authorize: 授权规则数据
        :param task_index: 任务号，用于并发任务时表示任务ID
        :return: 清洗后的授权信息列表
        :raises: ApiResultError 校验授权信息出错
        """

        # 获取授权数据
        account_rules = [{"bk_biz_id": self.bk_biz_id, "dbname": dbname} for dbname in authorize.access_dbs]
        source_ips = [item["ip"] if isinstance(item, dict) else item for item in authorize.source_ips]
        authorize_data = {
            "bk_biz_id": self.bk_biz_id,
            "operator": self.operator,
            "user": authorize.user,
            "account_rules": account_rules,
            "source_ips": source_ips,
            "target_instances": authorize.target_instances,
            "cluster_type": authorize.cluster_type,
        }

        try:
            # 这里需要authorize_data副本去请求参数，否则会带上app_code/app_secret
            resp = MySQLPrivManagerApi.pre_check_authorize_rules(params=copy.deepcopy(authorize_data), raw=True)
            pre_check = resp["code"] == 0
            message = resp["message"]
        except ApiResultError as e:
            # 捕获接口返回结果异常
            pre_check, message = False, _("「接口返回结果异常」{}").format(e.message)
        except Exception as e:
            # 捕获接口其他未知异常
            pre_check, message = False, _("「接口调用异常」{}").format(e)

        # 缓存当前的授权数据，并把前置检查结果返回
        authorize_data.update({"message": message, "index": task_index or 0})
        authorize_uid = data_cache(key=None, data=[authorize_data], cache_time=AUTHORIZE_DATA_EXPIRE_TIME)
        return {
            "pre_check": pre_check,
            "message": message,
            "authorize_uid": authorize_uid,
            "authorize_data": authorize.to_dict(),
            "task_index": task_index,
        }

    def pre_check_excel_rules(self, excel_authorize: ExcelAuthorizeMeta) -> Dict:
        """
        清洗excel数据并且把清洗后的excel返回
        :param excel_authorize: excel文件对象
        :return: 清洗后的授权信息excel文件
        :raises: ApiResultError 校验授权信息出错
        """

        authorize_excel_data_list = excel_authorize.authorize_excel_data

        # 并发请求数据清洗接口
        tasks = []
        with ThreadPoolExecutor(max_workers=min(len(authorize_excel_data_list), settings.CONCURRENT_NUMBER)) as ex:
            for index, excel_data in enumerate(authorize_excel_data_list):
                authorize = AuthorizeMeta.from_excel_data(excel_data, cluster_type=excel_authorize.cluster_type)
                tasks.append(ex.submit(self.pre_check_rules, authorize=authorize, task_index=index))

        # 整理请求结果和错误信息
        raw_authorize_data_list: List[Union[None, AuthorizeMeta]] = [
            None for _ in range(len(authorize_excel_data_list))
        ]
        to_cache_data_list: List[Dict[str, Any]] = [{} for _ in range(len(authorize_excel_data_list))]
        to_delete_cache_uid_list: List[str] = []
        pre_check: bool = True

        for future in as_completed(tasks):
            # 获取线程执行的授权结果
            task_result = future.result()
            uid, index = task_result["authorize_uid"], task_result["task_index"]

            # 将缓存数据取出放到excel缓存数据的切片中
            data = cache.get(uid)[0]
            pre_check &= task_result["pre_check"]

            to_delete_cache_uid_list.append(uid)
            to_cache_data_list[index] = data
            raw_authorize_data_list[index] = task_result["authorize_data"]

        # 缓存excel授权数据，删除线程中pre_check产生的缓存，并返回校验结果
        cache.delete_many(to_delete_cache_uid_list)
        authorize_uid = data_cache(key=None, data=to_cache_data_list, cache_time=AUTHORIZE_DATA_EXPIRE_TIME)
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/mysql/bizs/{self.bk_biz_id}/permission/authorize"
            f"/get_authorize_info_excel/?authorize_uid={authorize_uid}"
        )

        return {
            "pre_check": pre_check,
            "excel_url": excel_url,
            "authorize_uid": authorize_uid,
            "authorize_data_list": raw_authorize_data_list,
        }

    def get_online_rules(self) -> List:
        """获取现网授权记录"""

        online_rules_list = MySQLPrivManagerApi.get_online_rules({"bk_biz_id": self.bk_biz_id})
        return online_rules_list

    def get_authorize_info_excel(self, excel_authorize: ExcelAuthorizeMeta) -> HttpResponse:
        """
        根据id获取授权信息的excel文件 (只会同时存在一种类型的id)
        - ticket_id: 获取授权执行excel文件
        - authorize_uid: 获取前置检查excel文件
        """

        excel_data_dict__list: List[Dict[str, Any]] = []
        excel_name: str = ""

        # 单据走来的excel下载
        if excel_authorize.ticket_id:
            excel_name = "authorize_results.xlsx"
            error_queryset = MySQLAuthorizeRecord.get_authorize_records_by_ticket(excel_authorize.ticket_id)
            excel_data_dict__list = [error_data.serialize_excel_data() for error_data in error_queryset]

        # 授权ID走来的excel下载
        if excel_authorize.authorize_uid:
            excel_name = "pre_check_rules_info.xlsx"
            authorize_data_dict__list = cache.get(excel_authorize.authorize_uid)
            excel_data_dict__list = [{} for _ in range(len(authorize_data_dict__list))]
            for data in authorize_data_dict__list:
                excel_data_dict__list[data["index"]] = ExcelAuthorizeMeta.serialize_excel_data(data)

        wb = ExcelHandler.serialize(excel_data_dict__list, template=AUTHORIZE_EXCEL_ERROR_TEMPLATE)
        return ExcelHandler.response(wb, excel_name)

    def get_host_in_authorize(self, host_filter_meta: HostInAuthorizeFilterMeta):
        ticket_id = host_filter_meta.ticket_id
        keyword = host_filter_meta.keyword

        # 获取过滤参数,支持逗号或者空格分隔
        if keyword:
            keyword_list = keyword.split(",") if "," in keyword else keyword.split()
        else:
            keyword_list = None

        details = Ticket.objects.get(id=ticket_id).details
        bk_host_ids, ip_whitelist = [], []
        for item in details["authorize_data"]["source_ips"]:
            if "bk_host_id" in item:
                bk_host_ids.append(item["bk_host_id"])
            elif not keyword_list or item["ip"] in keyword_list:
                ip_whitelist.append({"ip": item["ip"]})

        hosts = ResourceQueryHelper.search_cc_hosts(
            bk_biz_id=self.bk_biz_id, role_host_ids=bk_host_ids, keyword=keyword
        )
        return {"hosts": hosts, "ip_whitelist": ip_whitelist}

    def authorize_apply(
        self,
        request,
        user: str,
        access_db: str,
        source_ips: str,
        target_instance: str,
        app: str = "",
        bk_biz_id: int = 0,
        set_name: str = "",
        module_host_info: str = "",
        module_name_list: str = "",
        type: str = "",
        call_from: str = "",
        operator: str = "",
    ):
        """直接授权，兼容gcs老的授权方式"""

        def parse_domain(raw_domain):
            match = re.compile("^(.*?)[#|:]?(\d*)$").match(raw_domain)  # noqa
            if not match:
                raise DBPermissionBaseException(_("域名解析失败，请输入合法域名"))
            _domain, _port = match.group(1).rstrip("."), match.group(2)
            return _domain, _port

        if app:
            app_detail = ScrApi.common_query(params={"app": app, "columns": ["appid", "ccId"]})["detail"]
            if not app_detail:
                raise DBPermissionBaseException(_("无法查询app: {}相关信息，请检查app输入是否合法。").format(app))
            app_detail = app_detail[0]

        # 域名存在，则走dbm的授权方式，否则走gcs的授权方式
        domain, __ = parse_domain(target_instance)
        cluster = Cluster.objects.filter(
            clusterentry__entry=domain, clusterentry__cluster_entry_type=ClusterEntryType.DNS.value
        )
        bk_biz_id = int(bk_biz_id or app_detail["ccId"])
        if cluster.exists():
            if not bk_biz_id:
                raise DBPermissionBaseException(_("授权集群: [{}]。业务信息bk_biz_id为空请检查。").format(target_instance))
            if cluster.count() > 1:
                raise DBPermissionBaseException(_("授权域名: [{}]对应多个集群，请检查域名合法性。").format(target_instance))
            cluster = cluster.first()
            db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
            authorize_infos = {
                "bk_biz_id": bk_biz_id,
                "user": user,
                "access_dbs": [access_db],
                "source_ips": source_ips.split(","),
                "target_instances": [cluster.immute_domain],
                "cluster_type": cluster.cluster_type,
            }
            authorize_info_slz = MySQLAuthorizeRulesSerializer(
                data={"authorize_plugin_infos": [authorize_infos], "need_itsm": False}
            )
            authorize_info_slz.context["request"] = request
            authorize_info_slz.is_valid(raise_exception=True)

            ticket = Ticket.create_ticket(
                bk_biz_id=bk_biz_id,
                ticket_type=TicketType.MYSQL_AUTHORIZE_RULES
                if db_type == DBType.MySQL
                else TicketType.TENDBCLUSTER_AUTHORIZE_RULES,
                creator=operator or self.operator,
                remark=_("第三方请求授权"),
                details=authorize_info_slz.validated_data,
            )
            return {"task_id": str(ticket.id), "platform": "dbm"}
        else:
            params = {
                "app": app,
                "app_id": app_detail["appid"],
                "client_ip": source_ips,
                "call_user": user,
                "call_from": call_from or user,
                "db_name": access_db,
                "type": type,
                "target_ip": target_instance,
                # 补充gcs网关的鉴权信息
                "bk_username": operator or env.GCS_SCR_OPERATOR,
                "bk_app_code": settings.APP_CODE,
                "bk_app_secret": settings.SECRET_KEY,
            }
            # 填充Set，模块主机和模块列表信息
            if set_name:
                params["set_name"] = set_name
            if module_host_info:
                params["module_host_info"] = module_host_info
            if module_name_list:
                params["module_name_list"] = module_name_list

            data = GcsApi.cloud_privileges_asyn_bydbname(params)
            return {"task_id": str(data["job_id"]), "platform": "gcs"}

    def query_authorize_apply_result(self, task_id, platform):
        """查询第三方授权的执行结果"""
        if platform == "gcs":
            resp = GcsApi.cloud_service_status(params={"job_id": task_id})
            if resp["code"] == 0:
                status = TicketStatus.SUCCEEDED
            elif resp["code"] == 1:
                status = TicketStatus.RUNNING
            else:
                status = TicketStatus.FAILED
            msg = resp["msg"]
        else:
            ticket = Ticket.objects.get(id=task_id)
            status, msg = ticket.status, _("授权状态: {}").format(TicketStatus.get_choice_label(ticket.status))

        return {"status": status, "msg": msg}
