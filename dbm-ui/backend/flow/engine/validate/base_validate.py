"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import functools
import inspect
import ipaddress
import re
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.configuration.constants import AffinityEnum
from backend.db_meta.models import Cluster
from backend.flow.engine.validate.exceptions import DisasterToleranceLevelFailedException, TicketDataException


def validates_with(validator_func):
    """装饰器：用于关联函数与校验函数"""

    def decorator(main_func):
        # 添加校验函数信息到主函数的元数据中
        main_func.validator = validator_func
        return main_func

    return decorator


def validator_log_format(func):
    """日志打印验证装饰器 - 必须输入关键字参数：field, index, row_key"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 强制要求的关键字参数
        required_meta = ["field", "index", "row_key"]
        missing = [key for key in required_meta if key not in kwargs]
        if missing:
            raise ValueError(_("调用validator方法，必须传入关键字参数[{}]".format(",".join(required_meta))))

        # 提取元数据并从kwargs中移除
        meta = {key: kwargs.pop(key) for key in required_meta}

        # 准备原始函数参数
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        is_method = param_names and param_names[0] in ["cls", "self"]
        # 调用原始验证函数
        try:
            # 处理类方法/实例方法
            if is_method:
                # 第一个参数是cls或self
                context = args[0] if args else None
                # 剩余参数是验证函数的实际参数
                remaining_args = args[1:]
                # 调用函数
                if context is not None:
                    errors = func(context, *remaining_args, **kwargs)
                else:
                    errors = func(*remaining_args, **kwargs)
            else:
                # 普通函数/静态方法
                errors = func(*args, **kwargs)
        except TypeError as e:
            # 增强参数错误提示
            raise TypeError(_("验证函数参数错误: {}. 需要参数: {}".format(e, param_names))) from e

        # 处理错误结果
        if errors is None or (isinstance(errors, list) and not errors) or errors == "":
            return None

        # 返回完整结果
        return {"field": meta["field"], "errors": errors, "index": meta["index"], "row_key": meta["row_key"]}

    wrapper._universal_wrapped = True
    return wrapper


class BaseValidator:
    """
    flow 参数检验的基类
    这里打算存放一些通用的校验方法, 比如一些合法实例、合法ip、合法域名表达等等
    """

    def __new__(cls, ticket_data: dict):
        """
        @param ticket_data: 单据参数结构
        """
        # 基础判断，判断ticket_data是否是dict结构
        if not isinstance(ticket_data, dict):
            raise TicketDataException("ticket_data is not dict, check")
        # 执行callable方法
        instance = super().__new__(cls)
        instance.data = ticket_data
        return instance()  # 返回 __call__ 的结果

    def __call__(self):
        """
        初始callable方法，不同validator定义重写__call__逻辑
        """
        return None

    @staticmethod
    def create_log_tag(field, index, row_key):
        """创建打印日志标记字典"""
        return {"field": field, "index": index, "row_key": row_key}

    @classmethod
    @validator_log_format
    def pre_check_instance(cls, check_instance_list: list):
        """
        判断Instance字符串合法性表达，DBM平台Instance字符串表达式：{ipv4}:{port}
        """
        error_mag = ""
        pattern = r"""
                ^
                ((\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}))
                :
                (\d+)
                $
            """
        for instance in check_instance_list:
            if bool(re.match(pattern, instance, re.VERBOSE)):
                continue
            error_mag += f"{instance} is not a valid instance \n"

        return error_mag

    @classmethod
    @validator_log_format
    def pre_check_ip(cls, check_ip_list: list):
        """
        判断Instance字符串合法性表达，DBM平台ip字符串表达式：ipv4
        """
        error_mag = ""
        for ip in check_ip_list:
            try:
                ipaddress.IPv4Address(ip)
                continue
            except ipaddress.AddressValueError:
                error_mag += f"{ip} is not a valid ipv4 \n"

        return error_mag

    @classmethod
    @validator_log_format
    def pre_check_domain(cls, check_domain_list: list):
        """
        判断domain字符串合法性表达
        """
        pattern = re.compile("(?=^.{3,255}$)[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+")

        error_msg = ""
        for domain in check_domain_list:
            if bool(pattern.match(domain)):
                continue
            error_msg += f"{domain} is not a valid domain \n"

        return error_msg

    @classmethod
    @validator_log_format
    def pre_check_cluster_exist(cls, cluster_id_list: list):
        """
        根据判断cluster_id判断集群是否存在
        """
        error_msg = ""
        for cluster_id in cluster_id_list:
            try:
                Cluster.objects.get(id=cluster_id)
                continue
            except Cluster.DoesNotExist:
                error_msg += f"cluster_id[{cluster_id}] is not exist \n"

        return error_msg

    @classmethod
    @validator_log_format
    def pre_check_immute_domain_exist(cls, immute_domain: str):
        """
        判断集群主域名是否呗注册到
        """
        try:
            Cluster.objects.get(immute_domain=immute_domain)
            return f"immute_domain[{immute_domain}] is exist \n"
        except Cluster.DoesNotExist:
            return ""

    @classmethod
    def check_disaster_tolerance_level(cls, cluster: Cluster, hosts: List[Dict]) -> bool:
        """
        根据集群的容灾基级别，判断传入的主机列表信息，是否符合集群容灾基本要求
        如何符合要求，则返回True, 反之返回False
        @param cluster: 待判断集群元信息
        @param hosts: 待判断的机器园区列表信息，dict格式：{"ip":"x", "sub_zone_id":0, "rack_id": 0},
        其中ip是机器ip，sub_zone_id是园区id，rack_id是机架id
        """
        if cluster.disaster_tolerance_level in (
            AffinityEnum.NONE,
            AffinityEnum.CROSS_RACK,
            AffinityEnum.MAX_EACH_ZONE_EQUAL,
        ):
            # 这类容灾级别不需要判断容灾级别，属于没有要求
            return True

        distinct_sub_zones = set([int(i["sub_zone_id"]) if i["sub_zone_id"] else 0 for i in hosts])
        distinct_racks = set([int(i["rack_id"]) if i["rack_id"] else 0 for i in hosts])

        if cluster.disaster_tolerance_level == AffinityEnum.CROS_SUBZONE:
            # 属于跨园区的容灾级别，保证sub_zone_id至少要两个以上的
            if len(distinct_sub_zones) >= 2:
                return True
            return False
        if cluster.disaster_tolerance_level == AffinityEnum.SAME_SUBZONE:
            # 属于同园区（无机架要求）的容灾级别，保证sub_zone_id有且只有一个
            if len(distinct_sub_zones) == 1:
                return True
            return False
        if cluster.disaster_tolerance_level == AffinityEnum.SAME_SUBZONE_CROSS_SWTICH:
            # 属于同园区的容灾级别，保证sub_zone_id有且只有一个， 同时机架保证至少两个以上
            if len(distinct_sub_zones) == 1 and len(distinct_racks) >= 2:
                return True
            return False

        # 匹配不了以上的平台定义的容灾级别，直接报异常
        raise DisasterToleranceLevelFailedException(f"not support {cluster.disaster_tolerance_level}")
