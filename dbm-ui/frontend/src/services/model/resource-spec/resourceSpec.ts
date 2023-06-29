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

/**
 * 资源规格
 */
export default class ResourceSpec {
  cpu: {
    max: number,
    min: number
  };
  mem: {
    max: number,
    min: number
  };
  storage_spec: {
    mount_point: string,
    size: number,
    type: string,
  }[];
  device_class: string[];
  create_at: string;
  creator: string;
  desc: string;
  spec_cluster_type: string;
  spec_machine_type: string;
  spec_name: string;
  update_at: string;
  updater: string;
  spec_id: number;
  instance_num?: number;

  constructor(payload = {} as ResourceSpec) {
    this.cpu = payload.cpu;
    this.mem = payload.mem;
    this.storage_spec = payload.storage_spec;
    this.device_class = payload.device_class;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.desc = payload.desc;
    this.spec_cluster_type = payload.spec_cluster_type;
    this.spec_machine_type = payload.spec_machine_type;
    this.spec_name = payload.spec_name;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.spec_id = payload.spec_id;
    this.instance_num = payload.instance_num ?? 0;
  }
}
