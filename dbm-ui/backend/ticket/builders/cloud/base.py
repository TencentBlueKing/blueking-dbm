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

from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.consts import CloudDBHATypeEnum
from backend.ticket import builders


class BaseServiceOperateFlowParamBuilder(builders.FlowParamBuilder):
    def patch_ticket_data(self, ticket_data, extension_type, keep=False):
        """
        将组件的新增/删除/替换/重装信息与原部署信息进行组合

        新增: details: {new_xxx: {host_infos: [....]}, ...}
        删除: details: {old_xxx_ids: [1, 2, 3], ...}
        替换: details: {new_xxx: {host_infos: [...(一个元素)]}, old_xxx_id: 1, ...}
        重装: details: {xxx_ids: [1, 2, 3], ...}

        基本思想：所有的操作都可以转换为 *部署单据信息格式* 进行操作。
        单据格式化的目的：组件操作信息 = 原组件A,B,C部署信息 + 新组件D操作信息 ---> 组成部署单据
        eg：比如我准备替换id为1的drs，那么单据信息就是 原nginx,drs,dbha的部署信息 + 新替换的drs机器的信息组成部署单据去部署新的drs
        """

        # 如果keep为True，表明是多次patch，需要保持extension_info为上次状态，
        if not keep:
            extension_info = DBExtension.get_extension_info_in_cloud(bk_cloud_id=ticket_data["bk_cloud_id"])
        else:
            extension_info = ticket_data

        # 获得当前组件的机器信息
        if extension_type in CloudDBHATypeEnum.get_values():
            present_host_infos = extension_info["dbha"][extension_type]
        else:
            present_host_infos = extension_info[extension_type]["host_infos"]

        # 操作的key
        old_ext_id_key = f"old_{extension_type}_id"
        old_ext_ids_key = f"old_{extension_type}_ids"
        ext_ids_key = f"{extension_type}_ids"
        new_ext_key = f"new_{extension_type}"

        # 如果是替换情况，目前替换只考虑替换单台组件的情况
        if old_ext_id_key in ticket_data and new_ext_key in ticket_data:
            # 获取替换组件的index序
            extension_id__extension_index_map = {ext["id"]: index for index, ext in enumerate(present_host_infos)}
            old_ext_index = extension_id__extension_index_map[ticket_data.pop(old_ext_id_key)]

            # 获取旧组件信息，并暂存到old_ext/host_infos下
            extension_info[f"old_{extension_type}"]["host_infos"] = [copy.deepcopy(present_host_infos[old_ext_index])]

            # 将新的组件信息覆盖旧的组件信息
            new_ext_info = ticket_data.pop(new_ext_key)["host_infos"][0]
            new_ext_info = {**present_host_infos[old_ext_index], **new_ext_info}
            present_host_infos.clear()
            present_host_infos.append(new_ext_info)

        # 如果是新增情况，则直接将新增机器录入到host_infos中
        elif new_ext_key in ticket_data:
            # 获取新组建的信息
            new_ext_infos = ticket_data.pop(new_ext_key)["host_infos"]
            # 清空原组件的信息，并将新增的替换上去，作为部署信息
            present_host_infos.clear()
            present_host_infos.extend(new_ext_infos)
            # 添加账号密码
            if extension_type in [ExtensionType.DRS.lower(), *CloudDBHATypeEnum.get_values()]:
                self.padding_account_info(ticket_data["bk_cloud_id"], present_host_infos, extension_type)

        # 如果是删除情况，则直接将删除机器录入到host_infos中
        elif old_ext_ids_key in ticket_data:
            old_host_infos = [host for host in present_host_infos if host["id"] in ticket_data[old_ext_ids_key]]
            present_host_infos.clear()
            present_host_infos.extend(old_host_infos)

        # 如果是重装的情况，则直接将重装机器录入到host_infos中
        elif ext_ids_key in ticket_data:
            rep_host_infos = [host for host in present_host_infos if host["id"] in ticket_data[ext_ids_key]]
            present_host_infos.clear()
            present_host_infos.extend(rep_host_infos)

        ticket_data.update(extension_info)
        return ticket_data

    def padding_account_info(self, bk_cloud_id, host_infos, extension_type):
        """
        给主机填充原有的账号和密码，
        主要用drs和dbha的新增场景
        """
        if extension_type in CloudDBHATypeEnum.get_values():
            extension_type = ExtensionType.DBHA

        ext = DBExtension.get_latest_extension(bk_cloud_id=bk_cloud_id, extension_type=extension_type)
        user, pwd = ext.details["user"], ext.details["pwd"]
        for host in host_infos:
            host.update({"user": user, "pwd": pwd})

    @classmethod
    def padding_dbha_type(cls, ticket_data):
        """
        给dbha服务组件的主机填充dbha_type
        """
        for host in ticket_data["dbha"]["gm"]:
            host["dbha_type"] = CloudDBHATypeEnum.GM
        for host in ticket_data["dbha"]["agent"]:
            host["dbha_type"] = CloudDBHATypeEnum.AGENT
