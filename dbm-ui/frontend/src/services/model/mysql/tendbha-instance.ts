/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

import { utcDisplayTime } from '@utils';
export default class tendbhaInstance {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: number;
  host_info: {
    alive: number,
    biz: {
      id: number,
      name: string,
    },
    cloud_area: {
      id: number,
      name: string,
    },
    cloud_id: number,
    host_id: number,
    host_name?: string,
    ip: string,
    ipv6: string,
    meta: {
      bk_biz_id: number,
      scope_id: number,
      scope_type: string
    },
    scope_id: string,
    scope_type: string,
    os_name: string,
    bk_cpu?: number,
    bk_disk?: number,
    bk_mem?: number,
    os_type: string,
    agent_id: number,
    cpu: string,
    cloud_vendor: string,
    bk_idc_name?: string,
  };
  id: number;
  instance_address: string;
  ip: string;
  master_domain: string;
  permission: Record<'mysql_view', boolean>;
  port: number;
  role: string;
  slave_domain: string;
  spce_config: {
    count: number;
    cpu: {
      max: number;
      min: number;
    },
    device_class: string[];
    id: number;
    mem: {
      max: number;
      min: number;
    },
    name: string;
    qps: Record<any, any>;
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[]
  };
  status: string;
  version: string;

  constructor(payload = {} as tendbhaInstance) {
    this.bk_cloud_id = payload.bk_cloud_id || 0;
    this.bk_cloud_name = payload.bk_cloud_name || '';
    this.bk_host_id = payload.bk_host_id || 0;
    this.cluster_id = payload.cluster_id || 0;
    this.cluster_name = payload.cluster_name || '';
    this.cluster_type = payload.cluster_type || '';
    this.create_at = payload.create_at || '';
    this.db_module_id = payload.db_module_id || 0;
    this.host_info = payload.host_info || {};
    this.id = payload.id || 0;
    this.instance_address = payload.instance_address || '';
    this.ip = payload.ip || '';
    this.master_domain = payload.master_domain || '';
    this.permission = payload.permission || {};
    this.port = payload.port || 0;
    this.role = payload.role || '';
    this.slave_domain = payload.slave_domain || '';
    this.spce_config = payload.spce_config || {};
    this.status = payload.status || '';
    this.version = payload.version || '';
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
