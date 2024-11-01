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

import ClusterEntryDetailModel from '@services/model/cluster-entry/cluster-entry-details';

import http from '../http';

/**
 * 获取集群入口列表
 */
export const getClusterEntries = (params: {
  cluster_id: number;
  bk_biz_id: number;
  entry_type?: 'dns' | 'clb' | 'polaris' | 'clbDns';
}) =>
  http
    .get<ClusterEntryDetailModel[]>('/apis/cluster_entry/get_cluster_entries/', params)
    .then((data) => data.map((item) => new ClusterEntryDetailModel(item)));

/**
 * 修改集群访问入口
 */
export const updateClusterEntryConfig = (params: {
  cluster_id: number;
  cluster_entry_details: {
    cluster_entry_type: string;
    domain_name: string;
    target_instances: string[];
  }[];
}) => http.post<{ cluster_id?: number }>('/apis/cluster_entry/refresh_cluster_domain/', params);
