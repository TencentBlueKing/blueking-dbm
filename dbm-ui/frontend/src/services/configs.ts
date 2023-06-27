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

import http from './http';
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
  PlatConfListParams } from './types/configs';

/**
 * 查询平台配置列表
 */
export const getPlatformConfigList = (params: PlatConfListParams): Promise<ConfigListItem[]> => http.get('/apis/configs/list_platform_configs/', params);

/**
 * 查询平台配置详情
 */
export const getConfigBaseDetails = (params: PlatConfDetailsParams): Promise<ConfigBaseDetails> => http.get('/apis/configs/get_platform_config/', params);

/**
 * 编辑平台配置
 */
export const updatePlatformConfig = (params: PlatConfDetailsUpdateParams): Promise<ConfigSaveResult> => http.post('/apis/configs/upsert_platform_config/', params);

/**
 * 查询配置发布历史记录
 */
export const getConfigVersionList = (params: ConfigVersionParams): Promise<ConfigVersionListResult> => http.get('/apis/configs/list_config_version_history/', params);

/**
 * 查询配置发布记录详情
 */
export const getConfigVersionDetails = (params: ConfigVersionParams): Promise<ConfigVersionDetails> => http.get('/apis/configs/get_config_version_detail/', params);

/**
 * 查询配置项名称列表
 */
export const getConfigNames = (params: PlatConfDetailsParams): Promise<ParameterConfigItem[]> => http.get('/apis/configs/list_config_names/', params);

/**
 * 获取查询层级（业务、模块、集群）配置详情
 */
export const getLevelConfig = (params: GetLevelConfigParams): Promise<ConfigBaseDetails> => http.post('/apis/configs/get_level_config/', params);

/**
 * 查询业务配置列表
 */
export const getBusinessConfigList = (params: BizConfListParams): Promise<ConfigListItem[]> => http.get('/apis/configs/list_biz_configs/', params);

/**
 * 编辑层级（业务、模块、集群）配置
 */
export const updateBusinessConfig = (params: BizConfDetailsUpdateParams): Promise<ConfigListItem[]> => http.post('/apis/configs/upsert_level_config/', params);

/**
 * 获取业务拓扑树
 */
export const getBusinessTopoTree = (params: BizConfTopoTreeParams): Promise<BizConfTopoTreeModel[]> => http.get(`/apis/${params.db_type}/bizs/${params.bk_biz_id}/resource_tree/`, { cluster_type: params.cluster_type });
