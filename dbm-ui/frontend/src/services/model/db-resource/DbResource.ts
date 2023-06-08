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

export default class DbResource {
  agent_status: number;
  asset_id: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_cpu: number;
  bk_disk: number;
  bk_host_id: number;
  bk_host_innerip: string;
  bk_mem: number;
  city: string;
  city_id: string;
  consume_time: string;
  create_time: string;
  device_class: string;
  for_bizs: Array<{ bk_biz_id: number; bk_biz_name: string; }>;
  ip: string;
  label: string;
  net_device_id: string;
  rack_id: string;
  raid: string;
  resource_types: string[];
  status: string;
  storage_device: {
    [key: string]: {
      size: number;
      disk_id: string;
      disk_type: string;
      file_type: string;
    }
  };
  sub_zone: string;
  sub_zone_id: string;
  svr_type_name: string;
  update_time: string;

  constructor(payload = {} as DbResource) {
    this.agent_status = payload.agent_status;
    this.asset_id = payload.asset_id;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_cpu = payload.bk_cpu;
    this.bk_disk = payload.bk_disk;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_innerip = payload.bk_host_innerip;
    this.bk_mem = payload.bk_mem;
    this.city = payload.city;
    this.city_id = payload.city_id;
    this.consume_time = payload.consume_time;
    this.create_time = payload.create_time;
    this.device_class = payload.device_class;
    this.for_bizs = payload.for_bizs || [];
    this.ip  = payload.ip;
    this.label = payload.label;
    this.net_device_id = payload.net_device_id;
    this.rack_id = payload.rack_id;
    this.raid = payload.raid;
    this.resource_types = payload.resource_types || [];
    this.status = payload.status;
    this.storage_device = payload.storage_device || {};
    this.sub_zone = payload.sub_zone;
    this.sub_zone_id = payload.sub_zone_id;
    this.svr_type_name = payload.svr_type_name;
    this.update_time = payload.update_time;
  }
}
