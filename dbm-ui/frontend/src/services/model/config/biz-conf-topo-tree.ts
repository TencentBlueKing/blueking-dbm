/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { ConfLevels } from '@common/const';

/**
 * 业务拓扑树
 */
export default class BizConfTopoTree {
  children: BizConfTopoTree[];
  extra: {
    /** 模块字符集（模块树第二行展示用；后端 resource_tree 待补，缺失时第二行不展示该段） */
    charset?: string;
    domain: string;
    proxy_version: string;
    /** 存储层系列（模块树第二行展示用，即模块配置的 db_version） */
    version: string;
    /** 模块版本系列（模块树第二行展示用，与 charset 组合展示） */
    version_series?: string;
  };
  instance_id: number;
  instance_name: string;
  obj_id: ConfLevels;
  obj_name: string;

  constructor(payload = {} as BizConfTopoTree) {
    this.instance_id = payload.instance_id;
    this.instance_name = payload.instance_name;
    this.obj_id = payload.obj_id;
    this.obj_name = payload.obj_name;
    this.children = payload.children || [];
    this.extra = payload.extra;
  }
}
