"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import dataclasses


def dict_to_dataclass(data_dict, data_class):
    """将字典转换为数据类实例"""

    # 获取数据类的属性列表
    fields = data_class.__dataclass_fields__
    # 创建一个空的字典，用于存储转换后的数据
    data = {}
    # 遍历属性列表
    for field_name, field_type in fields.items():
        # 如果属性类型是数据类，则递归调用 dict_to_dataclass 函数
        if dataclasses.is_dataclass(field_type.type):
            field_data = data_dict.get(field_name)
            if field_data:
                field_data = dict_to_dataclass(field_data, field_type.type)
        # 否则，直接从字典中获取属性值
        else:
            field_data = data_dict.get(field_name)
        # 将属性值添加到数据字典中
        data[field_name] = field_data
    # 使用数据类的构造函数创建数据类实例
    return data_class(**data)
