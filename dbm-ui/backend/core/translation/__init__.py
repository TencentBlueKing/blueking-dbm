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

"""
国际化，一般的执行步骤：
1. 使用language_finder.py，找出文件夹下所有未添加国际化的中文，然后添加上对应的翻译函数
2. 翻译完成后，执行python manage.py makemessages创建中文和英文的django.po文件
（因为之前的翻译文件可能并没有添加上对应的翻译函数指定位置，在翻译的时候会出现报错，只需要将po文件删除从新创建django.po即可）
3. 使用translate.py文件将中文文件夹下的po文件转换成简体中文的po文件
4. 使用python manage.py compilemessages编译django.po文件为django.mo文件
"""
