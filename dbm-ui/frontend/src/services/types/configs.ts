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
 * 查询平台配置列表参数
 */
export interface PlatConfListParams {
  meta_cluster_type: string,
  conf_type: string,
}

/**
 * 查询平台配置详情参数
 */
export interface PlatConfDetailsParams {
  meta_cluster_type: string,
  conf_type: string,
  version: string
}

/**
 * 修改平台配置信息
 */
export interface PlatConfDetailsUpdateParams {
  conf_items: ParameterConfigItem[]
  version: string
  name: string
  description: string
  conf_type: string,
  confirm: number,
  meta_cluster_type: string,
  publish_description?: string
}

/**
 * 配置列表项
 */
export interface ConfigListItem {
  name: string,
  updated_at: string,
  updated_by: string,
  version: string
}

/**
 * 配置基础信息
 */
export interface ConfigBaseDetails {
  conf_items: ParameterConfigItem[]
  version: string
  name: string
  description: string
  updated_at?: string
  updated_by?: string
}

/**
 * 参数配置项
 */
export interface ParameterConfigItem {
  conf_name: string
  conf_name_lc?: string
  description: string
  flag_disable: number
  flag_locked: number
  need_restart: number
  value_allowed: string
  op_type: string,
  value_default?: string
  value_type?: string
  value_type_sub?: string,
  conf_value?: string,
  extra_info?: string,
  level_name?: string,
  leval_value?: string,
}

/**
 * 保存并发布返回信息
 */
export interface ConfigSaveResult {
  conf_file: string
  conf_type: string
  file_id: number
  is_published: number
  namespace: string
  revision: string
}

/**
 * 查询配置发布历史记录 | 查询配置发布记录详情 参数
 */
export interface ConfigVersionParams {
  meta_cluster_type: string
  conf_type: string
  version: string
  bk_biz_id: number
  level_name: ConfLevels
  level_value: string
  level_info?: string
  revision?: string
}

/**
 * 配置发布历史返回
 */
export interface ConfigVersionListResult {
  bk_biz_id: number | string
  conf_file: string
  level_name: string
  level_value: number | string
  namespace: string
  published: string
  versions: ConfigVersionItem[]
}

/**
 * 发布历史版本信息
 */
export interface ConfigVersionItem {
  conf_file: string
  created_at: string
  created_by: string
  description: string
  is_published: number
  revision: string
  rows_affected: number
}

/**
 * 发布历史版本详情
 */
export interface ConfigVersionDetails {
  configs: ConfigVersionDiffItem[]
  configs_diff: ConfigVersionDiffItem[]
  content: string
  created_at: string
  created_by: string
  description: string
  id: number
  is_published: number
  pre_revision: string
  revision: string
  name: string
  version: string
  rows_affected: number
  publish_description: string
  updated_at: string
  updated_by: string
}

/**
 * 发布历史版本详情配置Diff信息
 */
export interface ConfigVersionDiffItem {
  conf_name: string
  conf_value: string
  description: string
  extra_info: string
  flag_disable: number
  flag_locked: number
  level_name: string
  level_value: string
  op_type: string
  need_restart: number
  value_allowed: string
}

/**
 * 获取查询层级（业务、模块、集群）配置详情参数
 */
export interface GetLevelConfigParams{
  conf_type: string,
  meta_cluster_type: string,
  version: string,
  bk_biz_id?: number,
  level_name?: string,
  level_value?: number,
  level_info?: {
    module?: string,
    app?: string
  }
}

/**
 * 查询业务配置列表参数
 */
export interface BizConfListParams {
  meta_cluster_type: string,
  conf_type: string,
  bk_biz_id: number
}

/**
 * 修改业务配置信息
 */
export interface BizConfDetailsUpdateParams {
  meta_cluster_type: string,
  conf_type: string,
  bk_biz_id: number,
  version: string
  level_name: string,
  level_value: number,
  conf_items: ParameterConfigItem[]
  description: string
  confirm: number,
  publish_description?: string
  level_info?: any,
}

/**
 * 获取业务拓扑树参数
 */
export interface BizConfTopoTreeParams {
  cluster_type: string,
  db_type: string,
  bk_biz_id: number
}

