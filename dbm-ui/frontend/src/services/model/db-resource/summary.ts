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

import { DBTypeInfos, DBTypes, MachineTypes } from '@common/const';

export default class Summary {
  city: string;
  count: number;
  cpu_mem_summary?: string;
  dedicated_biz: number;
  device_class?: string;
  disk_summary?: {
    disk_id: string | number;
    disk_type: string;
    file_type: string;
    mount_point: string;
    size: number;
  }[];
  for_biz_name: string;
  spec_cluster_type?: DBTypes;
  spec_id?: number;
  spec_machine_type?: MachineTypes;
  spec_name?: string;
  sub_zone_detail: Record<
    number,
    {
      count: number;
      name: string;
    }
  >;

  constructor(payload = {} as Summary) {
    this.dedicated_biz = payload.dedicated_biz;
    this.for_biz_name = payload.for_biz_name;
    this.city = payload.city;
    this.spec_id = payload.spec_id;
    this.spec_name = payload.spec_name;
    this.spec_cluster_type = payload.spec_cluster_type;
    this.spec_machine_type = payload.spec_machine_type;
    this.device_class = payload.device_class;
    this.disk_summary = payload.disk_summary;
    this.cpu_mem_summary = payload.cpu_mem_summary;
    this.count = payload.count;
    this.sub_zone_detail = payload.sub_zone_detail;
  }

  get deviceDisplay() {
    if (this.disk_summary && this.disk_summary?.length > 0) {
      const diskInfo = this.disk_summary.map((item) => `${item.mount_point}:${item.size}G:${item.disk_type}`).join(';');
      return `${this.device_class} (${diskInfo})`;
    }
    return `${this.device_class}`;
  }

  get specTypeDisplay() {
    if (!this.spec_cluster_type || !this.spec_machine_type) {
      return '--';
    }
    const { machineList, name } = DBTypeInfos[this.spec_cluster_type] || {
      machineList: [],
      name: '',
    };
    const matchMachine = machineList.find(({ value }) => value === this.spec_machine_type);
    return matchMachine ? `${name} - ${matchMachine.label}` : '--';
  }

  get subzoneDetailDisplay() {
    return `${Object.values(this.sub_zone_detail)
      .map((item) => `${item.name}: ${item.count}`)
      .join(', ')};`;
  }
}
