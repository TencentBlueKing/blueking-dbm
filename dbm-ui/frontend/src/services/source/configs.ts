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

import http from '../http';
import type {
  BizConfDetailsUpdateParams,
  ConfigBaseDetails,
  ConfigListItem,
  ConfigVersionDetails,
  ConfigVersionListResult,
  ConfigVersionParams,
  GetLevelConfigParams,
  ParameterConfigItem,
  PlatConfDetailsParams,
  PlatConfDetailsUpdateParams,
} from '../types/configs';

const path = '/apis/configs';

/**
 * 查询配置发布记录详情
 */
export const getConfigVersionDetails = (params: ConfigVersionParams) => http.get<ConfigVersionDetails>(`${path}/get_config_version_detail/`, params);

/**
 * 获取查询层级（业务、模块、集群）配置详情
 */
export const getLevelConfig = (params: GetLevelConfigParams) => http.post<ConfigBaseDetails>(`${path}/get_level_config/`, params);

/**
 * 查询平台配置详情
 */
export const getConfigBaseDetails = (params: PlatConfDetailsParams) => http.get<ConfigBaseDetails>(`${path}/get_platform_config/`, params);

/**
 * 查询业务配置列表
 */
export const getBusinessConfigList = (params: {
  meta_cluster_type: string,
  conf_type: string,
  bk_biz_id: number
}) => http.get<ConfigListItem[]>(`${path}/list_biz_configs/`, params);

/**
 * 查询配置项名称列表
 */
export const getConfigNames = (params: PlatConfDetailsParams) => http.get<ParameterConfigItem[]>(`${path}/list_config_names/`, params);

/**
 * 查询配置发布历史记录
 */
export const getConfigVersionList = (params: ConfigVersionParams) => http.get<ConfigVersionListResult>(`${path}/list_config_version_history/`, params);

/**
 * 查询平台配置列表
 */
export const getPlatformConfigList = (params: {
  meta_cluster_type: string,
  conf_type: string,
}) => http.get<ConfigListItem[]>(`${path}/list_platform_configs/`, params);

/**
 * 保存模块部署配置
 */
export interface CreateModuleDeployInfo {
  bk_biz_id: number,
  conf_items: {
    conf_name: string,
    conf_value: string,
    op_type: string
  }[],
  version: string,
  meta_cluster_type: string,
  level_name: string,
  level_value: number,
  conf_type: string,
}

/**
 * 保存模块配置
 */
export const saveModulesDeployInfo = (params: CreateModuleDeployInfo) => http.post<CreateModuleDeployInfo>(`${path}/save_module_deploy_info/`, params);

/**
 * 编辑层级（业务、模块、集群）配置
 */
export const updateBusinessConfig = (params: BizConfDetailsUpdateParams) => http.post<ConfigListItem[]>(`${path}/upsert_level_config/`, params);

/**
 * 编辑平台配置
 */
export const updatePlatformConfig = (params: PlatConfDetailsUpdateParams) => http.post<{
  conf_file: string
  conf_type: string
  file_id: number
  is_published: number
  namespace: string
  revision: string
}>(`${path}/upsert_platform_config/`, params);
