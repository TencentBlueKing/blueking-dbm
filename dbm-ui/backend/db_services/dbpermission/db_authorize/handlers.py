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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple, Union

from django.conf import settings
from django.core.cache import cache
from django.http.response import HttpResponse
from django.utils.translation import ugettext as _

from backend import env
from backend.components import DBPrivManagerApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_services.dbpermission.constants import AUTHORIZE_DATA_EXPIRE_TIME, AccountType
from backend.db_services.dbpermission.db_authorize.dataclass import AuthorizeMeta, ExcelAuthorizeMeta
from backend.utils.cache import data_cache
from backend.utils.excel import ExcelHandler


class AuthorizeHandler(object):
    """
    封装授权相关的处理操作
    """

    EXCEL_ERROR_TEMPLATE = ""
    authorize_meta: AuthorizeMeta = None
    excel_authorize_meta: ExcelAuthorizeMeta = None
    account_type: AccountType = None

    def __init__(self, bk_biz_id: int, operator: str = None):
        """
        :param bk_biz_id: 业务ID
        :param operator: 操作者
        """

        self.bk_biz_id = bk_biz_id
        self.operator = operator

    @staticmethod
    def _get_user_info_map(account_type: str, bk_biz_id: int):
        """
        获取业务下制定账号类型的账号信息，返回用户名与用户信息的映射
        @param account_type: 账号类型
        @param bk_biz_id: 业务ID
        """
        user_data = DBPrivManagerApi.get_account(params={"cluster_type": account_type, "bk_biz_id": bk_biz_id})
        user_info_map = {user["user"]: user for user in user_data["results"]}
        return user_info_map

    def _pre_check_rules(self, authorize: AuthorizeMeta, **kwargs) -> Tuple[bool, str, Dict]:
        """
        前置检查的具体逻辑，需要返回三个参数
        @param authorize: 授权元数据
        @param user_db__rules: 当前的授权规则
        :return pre_check: 前置校验是否通过
        :return message: 检查信息
        :return authorize_data: 授权序列化数据.
        注：返回的数据需要带上account_id用于鉴权
        """
        raise NotImplementedError

    def pre_check_rules(self, authorize: AuthorizeMeta, task_index: int = None, **kwargs) -> Dict:
        """
        - 清洗规则数据
        :param authorize: 授权规则数据
        :param task_index: 任务号，用于并发任务时表示任务ID
        :return: 清洗后的授权信息列表
        :raises: ApiResultError 校验授权信息出错
        """
        pre_check, message, authorize_data = self._pre_check_rules(authorize, **kwargs)
        authorize_data.update({"message": message, "index": task_index or 0})
        authorize_uid = data_cache(key=None, data=[authorize_data], cache_time=AUTHORIZE_DATA_EXPIRE_TIME)
        return {
            "pre_check": pre_check,
            "message": message,
            "authorize_uid": authorize_uid,
            "authorize_data": authorize_data,
            "task_index": task_index,
        }

    def pre_check_excel_rules(self, excel_authorize: ExcelAuthorizeMeta, **kwargs) -> Dict:
        """
        清洗excel数据并且把清洗后的excel返回
        :param excel_authorize: excel文件对象
        :return: 清洗后的授权信息excel文件
        :raises: ApiResultError 校验授权信息出错
        """

        authorize_excel_data_list = excel_authorize.authorize_excel_data
        # 并发请求数据校验接口，这里使用并发的原因是考虑有些pre-check需要请求IO接口
        tasks = []
        with ThreadPoolExecutor(max_workers=min(len(authorize_excel_data_list), settings.CONCURRENT_NUMBER)) as ex:
            for index, excel_data in enumerate(authorize_excel_data_list):
                # 解析excel行数据，然后执行pre_check
                authorize = self.authorize_meta.from_excel_data(excel_data, cluster_type=excel_authorize.cluster_type)
                tasks.append(ex.submit(self.pre_check_rules, authorize=authorize, task_index=index, **kwargs))

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
        db_type = ClusterType.cluster_type_to_db_type(excel_authorize.cluster_type)
        # 下载excel的url中，mysql和tendbcluster同用一个路由
        route_type = DBType.MySQL.value if db_type == DBType.TenDBCluster else db_type
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/{route_type}/bizs/{self.bk_biz_id}/permission/authorize"
            f"/get_authorize_info_excel/?authorize_uid={authorize_uid}"
        )

        return {
            "pre_check": pre_check,
            "excel_url": excel_url,
            "authorize_uid": authorize_uid,
            "authorize_data_list": raw_authorize_data_list,
        }

    def _multi_user_pre_check_rules(self, authorize: AuthorizeMeta, users_key: str, **kwargs):
        """提供一个通用的多账户授权前置校验方案"""
        authorize_data_list: List[Dict] = []
        all_pre_check: bool = True
        message: str = _("前置校验成功")

        # 多个账号的授权规则分别校验
        for user in getattr(authorize, users_key):
            single_auth = self.authorize_meta.from_dict(authorize.to_dict())
            single_auth.user = user["user"]
            single_auth.access_dbs = user["access_dbs"]

            pre_check, msg, authorize_data = self._pre_check_rules(single_auth, **kwargs)
            if not pre_check:
                all_pre_check, message = False, msg
            authorize_data_list.append(authorize_data)

        # 缓存授权数据并返回前置校验结果
        authorize_uid = data_cache(key=None, data=authorize_data_list, cache_time=AUTHORIZE_DATA_EXPIRE_TIME)
        return {
            "pre_check": all_pre_check,
            "message": message,
            "authorize_uid": authorize_uid,
            "authorize_data": authorize_data_list,
        }

    def multi_user_pre_check_rules(self, authorize: AuthorizeMeta, **kwargs):
        """
        多个账号的前置校验，适合多账号的授权
        @param authorize: 授权规则数据
        @param kwargs: 其他参数
        """
        raise NotImplementedError

    def get_online_rules(self) -> List:
        """获取现网授权记录"""
        raise NotImplementedError

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
            excel_data_dict__list = self.authorize_meta.serializer_record_data(excel_authorize.ticket_id)

        # 授权ID走来的excel下载
        if excel_authorize.authorize_uid:
            excel_name = "pre_check_rules_info.xlsx"
            authorize_data_dict__list = cache.get(excel_authorize.authorize_uid)
            excel_data_dict__list = [{} for _ in range(len(authorize_data_dict__list))]
            for data in authorize_data_dict__list:
                excel_data_dict__list[data["index"]] = self.excel_authorize_meta.serialize_excel_data(data)

        wb = ExcelHandler.serialize(excel_data_dict__list, template=self.EXCEL_ERROR_TEMPLATE)
        return ExcelHandler.response(wb, excel_name)
