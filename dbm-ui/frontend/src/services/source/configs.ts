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

import ConfigItemChangeModel from '@services/model/config/config-item-change';
import ConfigNameChangeModel from '@services/model/config/config-name-change';

import http, { type IRequestPayload } from '../http';

const path = '/apis/configs';

/**
 * 参数配置项
 */
export interface ParameterConfigItem {
  conf_name: string;
  conf_name_lc?: string;
  conf_value?: string;
  /**
   * 参数来源（后端返回，区分系统内置与平台自定义）
   * - ''（空值）：系统定义且未修改，不显示删除/恢复操作
   * - 'def'：系统定义但平台修改成了自己的定义，显示「恢复初始值」
   * - 'plat'：平台自定义，显示「删除」
   */
  create_from?: '' | 'def' | 'plat';
  description: string;
  extra_info?: string;
  flag_disable?: number;
  flag_encrypt?: number;
  flag_locked?: number;
  flag_readonly?: number;
  flag_visible?: number;
  leval_value?: string;
  level_name?: string;
  need_restart?: number;
  op_type: string;
  up_level_value?: {
    conf_value: string;
    level_name: string;
    level_value: string;
  };
  value_allowed: string;
  value_default?: string;
  value_type: string;
  value_type_sub?: string;
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
    flag_readonly: number;
    flag_visible: number;
    level_name: string;
    level_value: string;
    need_restart: number;
    op_type: string;
    value_allowed: string;
  }[];
  configs_diff: ConfigVersionDetails['configs'];
  content: string;
  created_at: string;
  created_by: string;
  description: string;
  id: number;
  is_published: number;
  name: string;
  pre_revision: string;
  publish_description: string;
  revision: string;
  rows_affected: number;
  updated_at: string;
  updated_by: string;
  version: string;
}

/**
 * 查询配置发布记录详情
 */
export function getConfigVersionDetails(params: {
  bk_biz_id?: number;
  conf_type: string;
  level_info?: any;
  level_name?: string;
  level_value?: number;
  meta_cluster_type: string;
  revision?: string;
  version: string;
}) {
  return http.get<ConfigVersionDetails>(`${path}/get_config_version_detail/`, params);
}

/**
 * 获取查询层级（业务、模块、集群）配置详情
 */
export function getLevelConfig(
  params: {
    bk_biz_id?: number;
    conf_type: string;
    level_info?: {
      app?: string;
      module?: string;
    };
    level_name?: string;
    level_value?: number | string;
    meta_cluster_type: string;
    version?: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.post<{
    conf_items: ParameterConfigItem[];
    description: string;
    name: string;
    permission: Record<string, boolean>;
    updated_at?: string;
    updated_by?: string;
    version: string;
  }>(`${path}/get_level_config/`, params, payload);
}
/**
 * 查询平台配置详情
 */
export function getConfigBaseDetails(
  params: {
    conf_type: string;
    meta_cluster_type: string;
    version: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<{
    conf_items: ParameterConfigItem[];
    description: string;
    name: string;
    permission: Record<string, boolean>;
    updated_at?: string;
    updated_by?: string;
    version: string;
  }>(`${path}/get_platform_config/`, params, payload);
}

/**
 * 查询业务配置列表
 */
export function getBusinessConfigList(
  params: {
    bk_biz_id: number;
    conf_file?: string;
    conf_type: string;
    limit?: number;
    meta_cluster_type: string;
    offset?: number;
  },
  payload = {} as IRequestPayload,
) {
  return http
    .get<
      {
        name: string;
        permission: Record<string, boolean>;
        updated_at: string;
        updated_by: string;
        version: string;
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
export function getConfigNames(params: { conf_type: string; meta_cluster_type: string; version: string }) {
  return http.get<ParameterConfigItem[]>(`${path}/list_config_names/`, params);
}

/**
 * 查询配置发布历史记录
 */
export function getConfigVersionList(params: {
  bk_biz_id?: number;
  conf_type: string;
  level_info?: any;
  level_name?: string;
  level_value?: number;
  meta_cluster_type: string;
  revision?: string;
  version: string;
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
    conf_type: string;
    meta_cluster_type: string;
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
    description: string;
    op_type: string;
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
  bk_biz_id: number;
  conf_items: ParameterConfigItem[];
  conf_type: string;
  confirm: number;
  description: string;
  level_info?: any;
  level_name: string;
  level_value: number | string;
  meta_cluster_type: string;
  name: string;
  publish_description?: string;
  version: string;
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
  conf_type: string;
  confirm: number;
  description: string;
  meta_cluster_type: string;
  name: string;
  publish_description?: string;
  version: string;
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

// 获取模块信息
export function getModuleDetail(params: { module_id: number }) {
  return http.post<{
    alias_name: string;
    buffer_percent: string;
    charset: string;
    db_module_id: number;
    db_module_name: string;
    db_version: string;
    max_remain_mem_gb: string;
    sync_type: string;
    system_version: string;
  }>(`${path}/get_module_by_id/`, params);
}

/**
 * 查询平台配置变更记录（操作记录）
 */
export function getConfigNameChanges(
  params: {
    conf_file?: string;
    conf_name?: string;
    conf_type?: string;
    limit?: number;
    namespace: string;
    offset?: number;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<ConfigNameChangeModel[]>(`${path}/list_confname_changes/`, params, payload).then((data) => ({
    ...data,
    results: data.map((item) => new ConfigNameChangeModel(item)),
  }));
}

/**
 * 查询业务配置名称变更记录（操作记录）
 */
export function getConfigItemChanges(
  params: {
    bk_biz_id: number;
    conf_file?: string;
    conf_name?: string;
    conf_type?: string;
    level_name?: string;
    level_value?: number | string;
    limit?: number;
    namespace: string;
    offset?: number;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<ConfigItemChangeModel[]>(`${path}/list_confitem_changes/`, params, payload).then((data) => ({
    ...data,
    results: data.map((item) => new ConfigItemChangeModel(item)),
  }));
}

// 查询配置名称类型（数据类型与约束类型联动）
export function getListConfNameTypes(params: { limit?: number; offset?: number }) {
  return http.get<Record<string, string[]>>(`${path}/list_conf_name_types/`, params);
}

// 查询配置类型列表
export function getListConfTypes(params: { limit?: number; meta_cluster_type: string; offset?: number }) {
  return http.get<
    {
      conf_type: string;
      name: string;
      namespace: string;
    }[]
  >(`${path}/list_conf_types/`, params);
}

// 查询集群模块支持的配置文件列表
export function getListClusterModuleConfFiles(params: {
  bk_biz_id: number;
  cluster_id?: number;
  db_module_id?: number;
  deploy_versions?: string; // json
  limit?: number;
  meta_cluster_type: string;
  offset?: number;
}) {
  return http.get<
    {
      conf_file: string;
      conf_type: string;
      name: string;
      namespace: string;
    }[]
  >(`${path}/list_cluster_module_conf_files/`, params);
}

// 删除模块配置
export function deleteModuleConfig(params: { bk_biz_id: number; db_module_id: number; meta_cluster_type: string }) {
  return http.post(`${path}/delete_module_config/`, params);
}

// 恢复默认值
export function recoverDefaultConfigItem(params: {
  bk_biz_id: number;
  conf_file: string;
  conf_names: string[];
  conf_type: string;
  level_name: string;
  level_value: string;
  meta_cluster_type: string;
}) {
  return http.post(`${path}/recover_default_conf_item/`, params);
}

// 删除某个级别的配置文件
export function deleteLevelValue(params: {
  bk_biz_id?: number;
  conf_file: string;
  conf_type: string;
  level_name: string;
  level_value: number | string;
  meta_cluster_type: string;
}) {
  return http.post(`${path}/delete_level_value/`, params);
}

// 配置项定义和值合法性校验
export function validateConfItems(
  params: Array<{
    conf_name: string;
    flag_encrypt?: number;
    flag_locked?: number;
    flag_readonly?: number;
    flag_visible?: number;
    need_restart?: number;
    op_type: string;
    value_allowed: string;
    value_default: string;
    value_type: string;
    value_type_sub: string;
  }>,
) {
  return http.post(`${path}/validate_conf_items/`, params, { responseType: 'json' });
}

// 修改/新增/删除平台配置项定义
export function changeConfNames(params: {
  conf_file: string;
  conf_names: Array<{
    conf_name: string;
    conf_name_lc: string;
    description: string;
    flag_encrypt?: number;
    flag_locked?: number;
    flag_readonly?: number;
    flag_visible?: number;
    need_restart?: number;
    op_type: string;
    value_allowed: string;
    value_default: string;
    value_type: string;
    value_type_sub: string;
  }>;
  conf_type: string;
  meta_cluster_type: string;
}) {
  return http.post(`${path}/change_conf_names/`, params);
}

/**
 * 备份存储配置项
 */
export interface BackupConfigItem {
  conf_name: string;
  conf_value: string;
}

/**
 * 备份存储配置行
 */
export interface BackupConfigRow {
  bk_cloud_id: string;
  bk_cloud_name: string;
  conf_items: BackupConfigItem[];
  updated_at: string;
  updated_by: string;
}

/**
 * 查询备份存储配置列表 (COS)
 */
export function getBackupConfigList(
  params: { bk_biz_id: number; limit?: number; offset?: number },
  payload = {} as IRequestPayload,
) {
  return http.get<BackupConfigRow[]>(`${path}/list_cos_configs/`, params, payload);
}

/**
 * 新增/编辑备份存储配置 (复用 upsert_level_config)
 */
export function upsertBackupConfig(params: {
  bk_biz_id: number;
  conf_items: {
    conf_name: string;
    conf_value: string;
    flag_locked?: number;
    op_type: 'update' | 'remove' | 'add';
  }[];
  conf_type: string;
  confirm?: number;
  description?: string;
  level_name: string;
  level_value: number | string;
  meta_cluster_type?: string;
  version: string;
}) {
  return http.post<null>(`${path}/upsert_level_config/`, params);
}

/**
 * 编辑层级（业务、模块、集群）配置
 */
export function upsertCommonLevelConfig(params: {
  bk_biz_id: number;
  conf_items: Array<{
    conf_name: string;
    conf_value: string;
    description?: string;
    flag_locked?: number;
    op_type: 'update' | 'remove' | 'add';
  }>;
  conf_type: string;
  confirm?: number;
  description?: string;
  level_info?: {
    description?: Record<string, string>;
  };
  level_name: string;
  level_value: number | string;
  meta_cluster_type: string;
  publish_description?: string;
  version: string;
}) {
  return http.post<null>(`${path}/upsert_common_level_config/`, params);
}

/**
 * 删除备份存储配置
 */
export function deleteBackupConfig(params: {
  bk_biz_id: number;
  conf_file?: string;
  conf_type?: string;
  level_name: string;
  level_value: number | string;
  meta_cluster_type?: string;
  version?: string;
}) {
  return http.post<null>(`${path}/delete_level_value/`, params);
}

/**
 * 备份存储配置项
 */
export interface BackupConfigItem {
  conf_name: string;
  conf_value: string;
}

/**
 * 备份存储配置行
 */
export interface BackupConfigRow {
  bk_cloud_id: string;
  bk_cloud_name: string;
  conf_items: BackupConfigItem[];
  permission: Record<string, boolean>;
  updated_at: string;
  updated_by: string;
}

/**
 * 克隆模块查询 - 单个参数项
 */
export interface CloneConfItem {
  conf_name: string;
  conf_value: string;
  description?: string;
  /** 差异类型推断 */
  diff_type?: 'changed' | 'new' | 'none' | 'removed';
  flag_disable?: number;
  flag_encrypt?: number;
  flag_locked?: number;
  flag_readonly?: number;
  flag_visible?: number;
  /** 级别名称 */
  level_name: string;
  level_value: string;
  need_restart?: number;
  op_type?: string;
  /** 源版本值（对比用） */
  source_conf_value?: string;
  /** 级别：0=平台级(plat), 1=业务/应用级(app) */
  stage: number;
  /**
   * 上一级配置信息（克隆场景下通常为 null）
   */
  up_level_value?: {
    conf_value?: string;
    level_name?: string;
    level_value?: string | number;
  } | null;
  /** 允许值（如 "OFF | ON"） */
  value_allowed?: string;
  /** 默认值 */
  value_default?: string;
  /** 值来源推断 */
  value_source?: 'custom' | 'source';
  /** 值类型（如 STRING） */
  value_type?: string;
  /** 值子类型（如 ENUM） */
  value_type_sub?: string;
}

/**
 * 克隆模块配置查询对比结果
 */
export interface CloneModuleQueryResult {
  bk_biz_id: string;
  conf_file_info: {
    conf_file: string;
    conf_file_lc: string;
    conf_type: string;
    conf_type_lc: string;
    created_at: string;
    description: string;
    namespace: string;
    namespace_info: string;
    updated_at: string;
    updated_by: string;
  };
  /** 废弃的参数名列表（源版本有但新版本不兼容） */
  conf_names_deprecated: string[] | null;
  /** 值差异详情 { conf_name: { source?, target? } } */
  conf_names_value_diff: Record<string, string>;
  /** 值被修改过的参数名列表（自定义） */
  conf_names_value_modified: string[] | null;
  /** 参数内容（key=conf_name） */
  content: Record<string, CloneConfItem>;
  level_name: string;
  level_value: string;
}

export function moduleCloneQuery(params: {
  conf_type: string;
  meta_cluster_type: string;
  source_bk_biz_id: string;
  source_conf_file: string;
  source_module_id: string;
  target_bk_biz_id: string;
  target_conf_file: string;
  target_module_id?: string | number;
}) {
  return http.post<CloneModuleQueryResult>(`${path}/module_clone_query/`, params);
}

/**
 * 检查配置项名称是否已存在
 */
export function checkConfNameExists(params: {
  conf_file: string;
  conf_name: string;
  conf_type?: string;
  meta_cluster_type: string;
}) {
  return http.get<{ exists: boolean }>(`${path}/check_conf_name_exists/`, params);
}
