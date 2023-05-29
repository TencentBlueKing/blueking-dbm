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

import http from './http';
import type {
  CheckIpParams,
  CloudAreaInfo,
  FetchHostDetailsParams,
  FetchHostInfosParams,
  FetchHostTopoParams,
  HostDetails,
  HostTopoInfo,
} from './types/ip';

/**
 * 根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息
 */
export const checkHost = (params: CheckIpParams) => http.post('/apis/ipchooser/host/check/', params);

/**
 * 根据主机关键信息获取机器详情信息
 */
export const getHostDetails = (params: FetchHostDetailsParams): Promise<HostDetails[]> => http.post('/apis/ipchooser/host/details/', params);

/**
 * 获取自定义配置，比如表格列字段及顺序
 */
export const getIpSelectorSettings = () => http.post('/apis/ipchooser/settings/batch_get/');

/**
 * 保存用户自定义配置
 */
export const updateIpSelectorSettings = (params: any) => http.post('/apis/ipchooser/settings/set/', params);

/**
 * 根据多个拓扑节点与搜索条件批量分页查询所包含的主机 ID 信息
 */
export const getHostIdInfos = (params: FetchHostInfosParams) => http.post('/apis/ipchooser/topo/query_host_id_infos/', params);

/**
 * 根据多个拓扑节点与搜索条件批量分页查询所包含的主机信息
 */
export const getHosts = (params: FetchHostInfosParams) => http.post('/apis/ipchooser/topo/query_hosts/', params);

/**
 * 批量获取含各节点主机数量的拓扑树
 */
export const getHostTopo = (params: FetchHostTopoParams) => http.post('/apis/ipchooser/topo/trees/', params);

/**
 * 查询主机拓扑信息
 */
export const getHostTopoInfos = (params: {
  bk_biz_id: number,
  filter_conditions: {
    bk_host_innerip?: string[],
    bk_host_id?: string[],
    mode?: string
  }
}): Promise<{total: number, hosts_topo_info: Array<HostTopoInfo>}> => http.post('/apis/ipchooser/topo/query_host_topo_infos/', params);

/**
 * 获取云区域列表
 */
export const getCloudList = (): Promise<CloudAreaInfo[]> => http.post('/apis/ipchooser/settings/search_cloud_area/');

/**
 * 查询磁盘类型
 */
export const searchDeviceClass = () => http.get<string[]>('/apis/ipchooser/settings/search_device_class/');
