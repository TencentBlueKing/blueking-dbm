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

/** */
export interface BaseResponse<T> {
  code: number | string,
  data: T,
  message: string,
  request_id: string
}

/**
 * 列表基础类型
 */
export interface ListBase<T> {
  count: number,
  next: string,
  previous: string,
  results: T
}

/**
 * 业务信息
 */
export interface BizItem {
  bk_biz_id: number,
  english_name: string,
  display_name: string,
  pinyin_name: string,
  pinyin_head: string,
  name: string,
  permission: {
    db_manage: boolean
  }
}

/**
 * 模块信息
 */
export interface ModuleItem {
  bk_biz_id: number,
  db_module_id: number,
  name: string,
}

/**
 * 获取模块参数
 */
export interface GetModulesParams {
  bk_biz_id: number,
  cluster_type: string,
}

/**
 * 获取人员列表参数
 */
export interface GetUsesParams {
  limit?: number,
  offset?: number,
  fuzzy_lookups?: string
}

/**
 * 人员列表信息
 */
export interface UseItem {
  display_name: string,
  username: string,
}

/**
 * 个人配置信息
 */
export interface ProfileItem {
  label: string,
  values: any
}

/**
 * 个人配置信息返回结果
 */
export interface ProfileResult {
  profile: ProfileItem[],
  username: string,
  is_manager: boolean
}

/**
 * 无权限返回
 */
export interface Permission {
  apply_url: string,
  permission: {
    actions: PermissionAction[],
    system_id: string,
    system_name: string
  }
}
export interface PermissionAction {
  id: string,
  name: string,
  related_resource_types: PermissionRelated[]
}
export interface PermissionRelated {
  instances: PermissionRelatedInstance[][]
  system_id: string,
  system_name: string,
  type: string,
  type_name: string
}
export interface PermissionRelatedInstance {
  id: string,
  name: string,
  type: string,
  type_name: string
}

/**
 * 节点详情
 */
export interface HostNode {
  bk_os_name: string,
  bk_host_id: number,
  bk_cloud_id: number,
  bk_host_innerip_v6: string,
  bk_host_name: string,
  bk_os_type: number | string,
  bk_host_innerip: string,
  status: number,
  bk_agent_id: string,
  bk_cloud_name: string,
  bk_cloud_vendor: null,
  bk_cpu: number,
  bk_mem: number,
  instance_num: number,
}

/**
 * 用于提交的节点数据
 */
export interface HostNodeForSubmit {
  bk_host_id?: number,
  ip: string
}

/**
 * 搜索过滤返回结果
 */
export interface SearchFilterItem {
  id: number | string,
  name: string,
}

/**
 * 校验资源权限参数
 */
export interface IAMParams {
  action_ids: Array<string>,
  resources: Array<{ type: string, id: string | number }>
}
