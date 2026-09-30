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
from typing import Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from django.utils.translation import gettext_lazy as _

from backend.db_meta.dataclass import DBModuleComponentVersion
from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, MachineType
from backend.db_meta.exceptions import DBModuleVersionException
from backend.db_meta.models.db_version import DBVersion
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum

# 组件绑定的介质包类型。TenDBCluster 的存储/接入介质在发行版上挂的 db_type 也是 MySQL。
MODULE_COMPONENT_PKG_TYPE: Dict[str, str] = {
    MachineType.SINGLE.value: MediumEnum.MySQL.value,
    MachineType.BACKEND.value: MediumEnum.MySQL.value,
    MachineType.REMOTE.value: MediumEnum.MySQL.value,
    MachineType.PROXY.value: MediumEnum.MySQLProxy.value,
    MachineType.SPIDER.value: MediumEnum.Spider.value,
}


class PackageOs(NamedTuple):
    """版本介质包支持的操作系统。os_names 为空列表表示不限制操作系统。"""

    os_type: str
    os_names: List[str]


def enabled_package_os(db_version_ids: Iterable[int]) -> Dict[int, PackageOs]:
    """各版本已启用介质包支持的操作系统，没有已启用介质包的版本不在结果里。

    一个版本只允许上传一个介质包，有多个已启用时取最早上传的那个。
    """
    packages = (
        Package.objects.filter(db_version_id__in=set(db_version_ids), enable=True)
        .order_by("id")
        .values_list("db_version_id", "permit_os_type", "permit_os")
    )
    result = {}
    for db_version_id, os_type, os_names in packages:
        result.setdefault(db_version_id, PackageOs(os_type, list(os_names or [])))
    return result


def effective_permit_os(layer: DBModuleComponentVersion, package_os: Mapping[int, PackageOs]) -> Optional[List[str]]:
    """模块这一层实际允许的操作系统。

    指定范围时用模块上保存的列表；跟随版本包时用介质包的列表，空列表表示不限制。
    跟随版本包但查不到这个操作系统类型的已启用介质包时返回 None。
    """
    if not layer.follow_package:
        return list(layer.permit_os)

    package = package_os.get(layer.db_version_id)
    if not package or package.os_type != layer.permit_os_type:
        return None
    return package.os_names


def get_layer_permit_os(db_module, access_layer: str) -> Optional[Tuple[str, Optional[List[str]]]]:
    """模块某一层当前允许的操作系统，返回 (操作系统类型, 操作系统列表)。

    列表的含义见 effective_permit_os。这一层还没设置版本时返回 None。
    """
    layer = db_module.current_db_version.get(_layer_component(db_module.cluster_type, access_layer))
    if not layer:
        return None
    return layer.permit_os_type, effective_permit_os(layer, enabled_package_os([layer.db_version_id]))


def validate_components(components: Mapping[str, DBModuleComponentVersion]) -> None:
    """校验各组件绑定的版本可用、介质类型匹配、操作系统在介质包范围内。"""
    version_ids = {layer.db_version_id for layer in components.values()}
    versions = DBVersion.objects.in_bulk(version_ids)
    package_os = enabled_package_os(version_ids)
    for component, layer in components.items():
        _validate_layer(component, layer, versions.get(layer.db_version_id), package_os.get(layer.db_version_id))


def _validate_layer(
    component: str, layer: DBModuleComponentVersion, db_version: Optional[DBVersion], package: Optional[PackageOs]
) -> None:
    version_id = layer.db_version_id
    if not db_version:
        raise DBModuleVersionException(message=_("版本 {} 不存在").format(version_id))
    if not db_version.enable:
        raise DBModuleVersionException(message=_("版本 {} 未启用").format(version_id))

    pkg_type = (db_version.distribution_snapshot or {}).get("pkg_type", "")
    if pkg_type != MODULE_COMPONENT_PKG_TYPE.get(component):
        raise DBModuleVersionException(message=_("组件 {} 不能绑定介质类型 {} 的版本 {}").format(component, pkg_type, version_id))

    if not package or package.os_type != layer.permit_os_type:
        raise DBModuleVersionException(message=_("版本 {} 没有 {} 类型的已启用介质包").format(version_id, layer.permit_os_type))

    # 介质包不限制操作系统时，模块指定任意操作系统都允许
    if not package.os_names:
        return

    rejected = [name for name in layer.permit_os if name not in package.os_names]
    if rejected:
        raise DBModuleVersionException(
            message=_("操作系统 {} 不在版本 {} 当前已启用介质包的范围内").format(",".join(rejected), version_id)
        )


def storage_version_series(modules: Sequence) -> Dict[int, str]:
    """各模块存储层版本的系列名。这一层还没设置版本时为空字符串。"""
    version_views = describe_modules_version(modules)
    series = {}
    for module in modules:
        storage = _layer_component(module.cluster_type, AccessLayer.STORAGE)
        series[module.db_module_id] = version_views[module.db_module_id].get(storage, {}).get("version_series", "")
    return series


def describe_module_version(module) -> Dict[str, Dict]:
    return describe_modules_version([module]).get(module.db_module_id, {})


def describe_modules_version(modules: Sequence) -> Dict[int, Dict[str, Dict]]:
    """批量展开模块各组件的版本信息，给接口展示用。

    返回示例: {模块ID: {"proxy": {...}, "backend": {...}}}，未设置版本的模块对应空字典。
    """
    layers_by_module = {module.db_module_id: module.current_db_version for module in modules}
    version_ids = {layer.db_version_id for layers in layers_by_module.values() for layer in layers.values()}
    versions = DBVersion.objects.select_related("version_series").in_bulk(version_ids)
    package_os = enabled_package_os(version_ids)

    result = {}
    for module_id, layers in layers_by_module.items():
        result[module_id] = {}
        for component, layer in layers.items():
            db_version = versions.get(layer.db_version_id)
            result[module_id][component] = _describe_layer(layer, db_version, effective_permit_os(layer, package_os))
    return result


def _describe_layer(
    layer: DBModuleComponentVersion, db_version: Optional[DBVersion], effective_os: Optional[List[str]]
) -> Dict:
    info = {
        **layer.to_dict(),
        "follow_package": layer.follow_package,
        "effective_permit_os": effective_os,
        "distribution": "",
        "version_series": "",
        "version_name": "",
        "full_version": "",
    }
    # 版本已被删除时只返回模块上保存的字段
    if not db_version:
        return info

    info["distribution"] = (db_version.distribution_snapshot or {}).get("name", "")
    info["version_series"] = db_version.version_series.name if db_version.version_series else ""
    info["version_name"] = db_version.name
    info["full_version"] = db_version.full_version
    return info


def _layer_component(cluster_type: str, access_layer: str) -> Optional[str]:
    """模块某一层对应的组件名，例如主从的存储层是 backend、TenDBCluster 的接入层是 spider。"""
    return ClusterMachineAccessTypeDefine.get(cluster_type, {}).get(access_layer)
