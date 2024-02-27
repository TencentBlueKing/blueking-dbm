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

import TimeBaseClassModel from '@services/util/time-base-class';

export default class SqlServerClusterDetail extends TimeBaseClassModel {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_entry_details: {
    cluster_entry_type: string;
    entry: string;
    role: string;
    target_details: {
      app: string;
      bk_cloud_id: number;
      dns_str: string;
      domain_name: string;
      domain_type: number;
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
  creator: string;
  db_module_name: string;
  id: number;
  master_domain: string;
  masters: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance?: string;
    ip: string;
    name: string;
    phase: string;
    port: number;
    spec_config: {
      id: number;
    };
    status: string;
  }[];
  operations: {
    cluster_id: number;
    flow_id: number;
    operator: string;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }[];
  phase: string;
  status: string;

  constructor(payload: SqlServerClusterDetail) {
    super(payload);
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_entry_details = payload.cluster_entry_details;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.creator = payload.creator;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.master_domain = payload.master_domain;
    this.masters = payload.masters;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.status = payload.status;
  }
}
