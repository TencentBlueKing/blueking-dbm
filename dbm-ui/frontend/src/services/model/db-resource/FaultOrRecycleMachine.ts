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
export default class FaultOrRecycleMachine {
  agent_status: number;
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_cpu: number;
  bk_disk: number;
  bk_host_id: number;
  bk_mem: number;
  city: string;
  create_at: string;
  creator: string;
  device_class: string;
  ip: string;
  os_name: string;
  pool: string;
  rack_id: string;
  sub_zone: string;
  ticket: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as FaultOrRecycleMachine) {
    this.agent_status = payload.agent_status;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cpu = payload.bk_cpu;
    this.bk_disk = payload.bk_disk;
    this.bk_host_id = payload.bk_host_id;
    this.bk_mem = payload.bk_mem;
    this.city = payload.city;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.device_class = payload.device_class;
    this.ip = payload.ip;
    this.os_name = payload.os_name;
    this.pool = payload.pool;
    this.rack_id = payload.rack_id;
    this.sub_zone = payload.sub_zone;
    this.ticket = payload.ticket;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }
}
