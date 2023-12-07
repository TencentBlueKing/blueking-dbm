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

import logging
import uuid
from typing import Any, Dict, List, NoReturn, Union

import pytest
from django.utils.module_loading import import_string
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion, ScheduleAssertion

from backend.db_meta.enums import ClusterType
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.tests.flow.components.collections.base import BaseComponentPatcher as Patcher
from backend.tests.flow.components.collections.base import BaseComponentTest
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.dns import DnsApiMock
from backend.tests.mock_data.components.job import JobApiMock
from backend.tests.mock_data.components.mysql_priv_manager import MySQLPrivManagerApiMock
from backend.tests.mock_data.flow.components.collections.mysql import MYSQL_SINGLE_APPLY_GLOBAL_DATA
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class MySQLComponentBaseTest(BaseComponentTest):
    """MySQL组件的自定义测试基类"""

    global_data: Union[Dict, Any] = None
    kwargs: Union[Dict, Any] = None
    trans_data: Union[Dict, Any] = None
    excepted_outputs: Dict = None

    @classmethod
    def _set_global_data(cls) -> None:
        """global data为单据参数，默认为mysql_single_apply单据参数"""
        cls.global_data = {}

    @classmethod
    def _set_trans_data(cls) -> None:
        """trans_data为上下文参数，子类可根据场景进行赋值"""
        cls.trans_data = {}

    @classmethod
    def _set_kwargs(cls) -> None:
        """kwargs为节点私有化参数，子类可根据场景进行赋值"""
        cls.kwargs = {}

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        """预期测试样例的输出结果"""
        raise NotImplementedError()

    @classmethod
    def setUpTestData(cls) -> Union[Any, NoReturn]:
        # 创建默认单据（类型默认为mysql_single_apply）
        # TODO: 是否需要根据组件不同而修改单据类型
        ticket_type = TicketType.MYSQL_SINGLE_APPLY.value
        Ticket.objects.create(id=1, creator="admin", updater="admin", bk_biz_id=1, ticket_type=ticket_type)

        # 创建Package数据
        package_common_data = {"creator": "admin", "updater": "admin", "size": 0, "md5": ""}
        for db_type in PackageType.get_values():
            if db_type in [PackageType.MySQL.value, PackageType.Proxy.value]:
                version = "MySQL-5.7"
            else:
                version = "latest"

            Package.objects.create(
                **package_common_data, version=version, name=db_type, pkg_type=db_type, path=f"/tmp/{db_type}/"
            )

    @classmethod
    def setUpClass(cls) -> Union[Any, NoReturn]:
        super().setUpClass()
        cls._set_global_data()
        cls._set_trans_data()
        cls._set_kwargs()
        cls._set_excepted_outputs()

    def to_mock_class_list(self) -> List:
        """需要mock的组件列表"""

        mock_class_list = [MySQLPrivManagerApiMock, DBConfigApiMock, JobApiMock, DnsApiMock, CCApiMock()]
        return mock_class_list

    def to_mock_path_list(self) -> List[str]:
        """需要mock的文件路径列表，默认是component所在的文件路径"""

        mock_path_list = [self.component_cls().__module__, BkJobService.__module__]
        return mock_path_list

    def get_patchers(self) -> List[Patcher]:
        """对相关属性、方法和组件进行mock。如果用户想自定义mock对象，也可覆写该方法"""

        patchers: List[Patcher] = []

        # mock组件
        for mock_class in self.to_mock_class_list():
            mock_class_name = getattr(mock_class, "__name__", None) or getattr(
                getattr(mock_class, "__class__"), "__name__"
            )
            if mock_class_name.endswith("Mock"):
                class_name = mock_class_name[:-4]
            else:
                class_name = mock_class_name

            for mock_path in self.to_mock_path_list():
                target = f"{mock_path}.{class_name}"
                try:
                    import_string(target)
                    patchers.append(Patcher(target=target, new=mock_class))
                except ImportError:
                    pass

        return patchers

    def get_schedule_assertions(self) -> List[ScheduleAssertion]:
        """对于组件有轮询场景的，可添加schedule_assertion进行断言"""
        return []

    def get_execute_assertion(self) -> ExecuteAssertion:
        """返回执行断言"""
        return ExecuteAssertion(success=True, outputs=self.excepted_outputs)

    def cases(self) -> List[ComponentTestCase]:
        return [
            ComponentTestCase(
                name=f"{self.component_cls().__name__}组件测试",
                inputs={"global_data": self.global_data, "trans_data": self.trans_data, "kwargs": self.kwargs},
                parent_data={},
                execute_assertion=self.get_execute_assertion(),
                schedule_assertion=self.get_schedule_assertions(),
                patchers=self.get_patchers(),
            )
        ]


class MySQLSingleApplyComponentTest(MySQLComponentBaseTest):
    """基于mysql_single_apply流程相关组件的测试基类"""

    @classmethod
    def _set_global_data(cls) -> None:
        cls.global_data = MYSQL_SINGLE_APPLY_GLOBAL_DATA

    @classmethod
    def _set_kwargs(cls) -> None:
        trans_files = GetFileList()
        act_kwargs = {
            "get_trans_data_ip_var": SingleApplyAutoContext.get_new_ip_var_name(),
            "file_list": trans_files.mysql_install_package(db_version=cls.global_data["db_version"]),
            "cluster_type": ClusterType.TenDBSingle,
            "is_update_trans_data": True,
        }
        cls.kwargs = act_kwargs
        cls.kwargs.update({"root_id": uuid.uuid1().hex, "node_id": uuid.uuid1().hex, "node_name": "Component"})

    @classmethod
    def get_schedule_assertions(cls) -> List[ScheduleAssertion]:
        return [
            ScheduleAssertion(success=True, schedule_finished=True, outputs=cls.excepted_outputs, callback_data=None)
        ]
