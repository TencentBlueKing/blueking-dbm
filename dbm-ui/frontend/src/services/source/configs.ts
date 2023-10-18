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

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';

import http from '../http';
import type {
  BizConfDetailsUpdateParams,
  BizConfListParams,
  BizConfTopoTreeParams,
  ConfigBaseDetails,
  ConfigListItem,
  ConfigSaveResult,
  ConfigVersionDetails,
  ConfigVersionListResult,
  ConfigVersionParams,
  GetLevelConfigParams,
  ParameterConfigItem,
  PlatConfDetailsParams,
  PlatConfDetailsUpdateParams,
  PlatConfListParams,
} from '../types/configs';
import type {
  CreateModuleDeployInfo,
} from '../types/ticket';

const path = '/apis/configs';

// TODO INTERFACE /apis/cmdb/bizs/

/**
 * 查询配置发布记录详情
 */
// eslint-disable-next-line max-len
// export const getConfigVersionDetails = (params: ConfigVersionParams) => http.get<ConfigVersionDetails>('/apis/configs/get_config_version_detail/', params);

/**
 * 获取查询层级（业务、模块、集群）配置详情
 */
export const getLevelConfig = (params: GetLevelConfigParams) => http.post<ConfigBaseDetails>(`${path}/get_level_config/`, params);

/**
 * 查询平台配置详情
 */
// eslint-disable-next-line max-len
// export const getConfigBaseDetails = (params: PlatConfDetailsParams) => http.get<ConfigBaseDetails>('/apis/configs/get_platform_config/', params);

/**
 * 查询业务配置列表
 */
// eslint-disable-next-line max-len
// export const getBusinessConfigList = (params: BizConfListParams) => http.get<ConfigListItem[]>('/apis/configs/list_biz_configs/', params);

/**
 * 查询配置项名称列表
 */
export const getConfigNames = (params: PlatConfDetailsParams) => http.get<ParameterConfigItem[]>(`${path}/list_config_names/`, params);

/**
 * 查询配置发布历史记录
 */
// eslint-disable-next-line max-len
// export const getConfigVersionList = (params: ConfigVersionParams) => http.get<ConfigVersionListResult>('/apis/configs/list_config_version_history/', params);

/**
 * 查询平台配置列表
 */
// eslint-disable-next-line max-len
// export const getPlatformConfigList = (params: PlatConfListParams) => http.get<ConfigListItem[]>('/apis/configs/list_platform_configs/', params);

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
// eslint-disable-next-line max-len
// export const updatePlatformConfig = (params: PlatConfDetailsUpdateParams) => http.post<ConfigSaveResult>('/apis/configs/upsert_platform_config/', params);
