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
import { differenceInSeconds } from 'date-fns';

import type { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

import { utcDisplayTime } from '@utils';

export default class ResourceSpec {
  capacity: number;
  cpu: {
    max: number;
    min: number;
  };
  create_at: string;
  creator: string;
  desc: string;
  device_class: string[];
  enable: boolean;
  instance_num: number;
  is_refer: boolean;
  mem: {
    max: number;
    min: number;
  };
  permission: {
    spec_create: boolean;
    spec_delete: boolean;
    spec_update: boolean;
  };
  qps: {
    max: number;
    min: number;
  };
  spec_cluster_type: ClusterTypes;
  spec_db_type: DBTypes;
  spec_id: number;
  spec_machine_type: MachineTypes;
  spec_name: string;
  storage_spec: {
    mount_point: string;
    size: number;
    type: string;
  }[];
  update_at: string;
  updater: string;

  constructor(payload = {} as ResourceSpec) {
    this.capacity = payload.capacity;
    this.cpu = payload.cpu;
    this.mem = payload.mem;
    this.storage_spec = payload.storage_spec;
    this.device_class = payload.device_class;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.desc = payload.desc;
    this.enable = payload.enable;
    this.spec_db_type = payload.spec_db_type;
    this.spec_cluster_type = payload.spec_cluster_type;
    this.spec_machine_type = payload.spec_machine_type;
    this.spec_name = payload.spec_name;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.spec_id = payload.spec_id;
    this.is_refer = payload.is_refer;
    this.instance_num = payload.instance_num ?? 0;
    this.qps = payload.qps || {};
    this.permission = payload.permission || {};
  }

  get isRecentSeconds() {
    const createDay = new Date(this.create_at);
    const today = new Date();
    return differenceInSeconds(today, createDay) < 30;
  }

  get name() {
    return this.spec_name;
  }

  get qpsText() {
    if (this.qps) {
      return `${this.qps.min} ~ ${this.qps.max}`;
    }

    return '--';
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
