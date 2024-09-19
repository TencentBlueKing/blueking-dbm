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

import http, { type IRequestPayload } from '../http';

const path = '/apis/configs';

/**
 * 参数配置项
 */
interface ParameterConfigItem {
  conf_name: string;
  conf_name_lc?: string;
  description: string;
  flag_disable: number;
  flag_locked: number;
  need_restart: number;
  value_allowed: string;
  op_type: string;
  value_default?: string;
  value_type?: string;
  value_type_sub?: string;
  conf_value?: string;
  extra_info?: string;
  level_name?: string;
  leval_value?: string;
}

/**
 * 发布历史版本详情
 */
interface ConfigVersionDetails {
  configs: {
    conf_name: string;
    conf_value: string;
    description: string;
    extra_info: string;
    flag_disable: number;
    flag_locked: number;
    level_name: string;
    level_value: string;
    op_type: string;
    need_restart: number;
    value_allowed: string;
  }[];
  configs_diff: ConfigVersionDetails['configs'];
  content: string;
  created_at: string;
  created_by: string;
  description: string;
  id: number;
  is_published: number;
  pre_revision: string;
  revision: string;
  name: string;
  version: string;
  rows_affected: number;
  publish_description: string;
  updated_at: string;
  updated_by: string;
}

/**
 * 查询配置发布记录详情
 */
export function getConfigVersionDetails(params: {
  meta_cluster_type: string;
  conf_type: string;
  version: string;
  bk_biz_id?: number;
  level_name?: string;
  level_value?: number;
  level_info?: any;
  revision?: string;
}) {
  return http.get<ConfigVersionDetails>(`${path}/get_config_version_detail/`, params);
}

/**
 * 获取查询层级（业务、模块、集群）配置详情
 */
export function getLevelConfig(
  params: {
    conf_type: string;
    meta_cluster_type: string;
    version?: string;
    bk_biz_id?: number;
    level_name?: string;
    level_value?: number;
    level_info?: {
      module?: string;
      app?: string;
    };
  },
  payload = {} as IRequestPayload,
) {
  return http.post<{
    conf_items: ParameterConfigItem[];
    version: string;
    name: string;
    description: string;
    updated_at?: string;
    updated_by?: string;
  }>(`${path}/get_level_config/`, params, payload);
}
/**
 * 查询平台配置详情
 */
export function getConfigBaseDetails(
  params: {
    meta_cluster_type: string;
    conf_type: string;
    version: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<{
    conf_items: ParameterConfigItem[];
    version: string;
    name: string;
    description: string;
    updated_at?: string;
    updated_by?: string;
  }>(`${path}/get_platform_config/`, params, payload);
}

/**
 * 查询业务配置列表
 */
export function getBusinessConfigList(
  params: {
    meta_cluster_type: string;
    conf_type: string;
    bk_biz_id: number;
  },
  payload = {} as IRequestPayload,
) {
  return http
    .get<
      {
        name: string;
        updated_at: string;
        updated_by: string;
        version: string;
        permission: Record<'dbconfig_edit', boolean>;
      }[]
    >(`${path}/list_biz_configs/`, params, payload)
    .then((data) =>
      data.map((item) => ({
        ...item,
        permission: item.permission || {},
      })),
    );
}

/**
 * 查询配置项名称列表
 */
export function getConfigNames(params: { meta_cluster_type: string; conf_type: string; version: string }) {
  return http.get<ParameterConfigItem[]>(`${path}/list_config_names/`, params);
}

/**
 * 查询配置发布历史记录
 */
export function getConfigVersionList(params: {
  meta_cluster_type: string;
  conf_type: string;
  version: string;
  bk_biz_id?: number;
  level_name?: string;
  level_value?: number;
  level_info?: any;
  revision?: string;
}) {
  return http.get<{
    bk_biz_id: number | string;
    conf_file: string;
    level_name: string;
    level_value: number | string;
    namespace: string;
    published: string;
    versions: {
      conf_file: string;
      created_at: string;
      created_by: string;
      description: string;
      is_published: number;
      revision: string;
      rows_affected: number;
    }[];
  }>(`${path}/list_config_version_history/`, params);
}

/**
 * 查询平台配置列表
 */
export function getPlatformConfigList(
  params: {
    meta_cluster_type: string;
    conf_type: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<
    {
      name: string;
      updated_at: string;
      updated_by: string;
      version: string;
    }[]
  >(`${path}/list_platform_configs/`, params, payload);
}

/**
 * 保存模块部署配置
 */
export function saveModulesDeployInfo(params: {
  bk_biz_id: number;
  conf_items: {
    conf_name: string;
    conf_value: string;
    op_type: string;
    description: string;
  }[];
  conf_type: string;
  level_name: string;
  level_value: number;
  meta_cluster_type: string;
  version: string;
}) {
  return http.post<{
    bk_biz_id: string;
    conf_file: string;
    conf_type: string;
    is_published: number;
    namespace: string;
    revision: string;
  }>(`${path}/save_module_deploy_info/`, params);
}

/**
 * 编辑层级（业务、模块、集群）配置
 */
export function updateBusinessConfig(params: {
  name: string;
  meta_cluster_type: string;
  conf_type: string;
  bk_biz_id: number;
  version: string;
  level_name: string;
  level_value: number;
  conf_items: ParameterConfigItem[];
  description: string;
  confirm: number;
  publish_description?: string;
  level_info?: any;
}) {
  return http.post<
    {
      name: string;
      updated_at: string;
      updated_by: string;
      version: string;
    }[]
  >(`${path}/upsert_level_config/`, params);
}

/**
 * 编辑平台配置
 */
export function updatePlatformConfig(params: {
  conf_items: ParameterConfigItem[];
  version: string;
  name: string;
  description: string;
  conf_type: string;
  confirm: number;
  meta_cluster_type: string;
  publish_description?: string;
}) {
  return http.post<{
    conf_file: string;
    conf_type: string;
    file_id: number;
    is_published: number;
    namespace: string;
    revision: string;
  }>(`${path}/upsert_platform_config/`, params);
}

// 更具模块 id 获取模块信息
export function getModuleDetail(params: { module_id: number }) {
  return http.post<{
    buffer_percent: string;
    charset: string;
    db_version: string;
    max_remain_mem_gb: string;
    sync_type: string;
    system_version: string;
  }>(`${path}/get_module_by_id/`, params);
}
