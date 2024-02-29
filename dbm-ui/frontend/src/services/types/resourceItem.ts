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

import { PipelineStatus } from '@common/const';

/**
 * mysql 资源信息
 */
export interface ResourceItem {
  bk_cloud_id: number;
  cluster_entry_details: {
    cluster_entry_type: string;
    entry: string;
    role: string;
    target_details: {
      app: string;
      bk_cloud_iduid: number;
      dns_str: string;
      domain_name: string;
      domain_typeuid: number;
      ip: string;
      last_change_time: string;
      manager: string;
      port: number;
      remark: string;
      start_time: string;
      status: string;
      uid: number;
    }[];
  }[];
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_name: string;
  db_module_id: number;
  id: number;
  master_domain: string;
  masters: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    ip: string;
    name: string;
    instance: string;
    port: number;
    status: 'running' | 'unavailable';
  }[];
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  phase: 'online' | 'offline';
  proxies?: ResourceItem['masters'];
  slaves?: ResourceItem['masters'];
  slave_domain: string;
  status: 'normal' | 'abnormal';
  isMaster: boolean;
}
