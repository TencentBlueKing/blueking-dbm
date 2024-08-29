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

import { MachineTypes } from '@common/const';

import { t } from '@locales/index';

export default class Summary {
  dedicated_biz: number;
  for_biz_name: string;
  city: string;
  spec_id?: number;
  spec_name?: string;
  spec_machine_type?: MachineTypes;
  device_class?: string;
  disk_summary?: string;
  cpu_mem_summary?: string;
  count: number;
  sub_zone_detail: Record<string, number>;

  constructor(payload = {} as Summary) {
    this.dedicated_biz = payload.dedicated_biz;
    this.for_biz_name = payload.for_biz_name;
    this.city = payload.city;
    this.spec_id = payload.spec_id;
    this.spec_name = payload.spec_name;
    this.spec_machine_type = payload.spec_machine_type;
    this.device_class = payload.device_class;
    this.disk_summary = payload.disk_summary;
    this.cpu_mem_summary = payload.cpu_mem_summary;
    this.count = payload.count;
    this.sub_zone_detail = payload.sub_zone_detail;
  }

  get device_display() {
    return `${this.device_class} (${this.disk_summary})`;
  }

  get spec_machine_display() {
    const machineTypeMap: Record<MachineTypes, string> = {
      [MachineTypes.SINGLE]: t('后端存储机型'),
      [MachineTypes.SPIDER]: t('接入层Master'),
      [MachineTypes.REMOTE]: t('后端存储规格'),
      [MachineTypes.PROXY]: t('Proxy机型'),
      [MachineTypes.BACKEND]: t('后端存储机型'),
      [MachineTypes.PREDIXY]: t('Proxy机型'),
      [MachineTypes.TWEMPROXY]: t('Proxy机型'),
      [MachineTypes.INFLUXDB]: t('后端存储机型'),
      [MachineTypes.RIAK]: t('后端存储机型'),
      [MachineTypes.BROKER]: t('Broker节点规格'),
      [MachineTypes.ZOOKEEPER]: t('Zookeeper节点规格'),
      [MachineTypes.REDIS]: t('后端存储机型'),
      [MachineTypes.TENDISCACHE]: t('后端存储机型'),
      [MachineTypes.TENDISSSD]: t('后端存储机型'),
      [MachineTypes.TENDISPLUS]: t('后端存储机型'),
      [MachineTypes.ES_DATANODE]: t('冷_热节点规格'),
      [MachineTypes.ES_MASTER]: t('Master节点规格'),
      [MachineTypes.ES_CLIENT]: t('Client节点规格'),
      [MachineTypes.HDFS_MASTER]: t('NameNode_Zookeeper_JournalNode节点规格'),
      [MachineTypes.HDFS_DATANODE]: t('DataNode节点规格'),
      [MachineTypes.MONGOS]: t('Mongos规格'),
      [MachineTypes.MONGODB]: t('ShardSvr规格'),
      [MachineTypes.MONGO_CONFIG]: t('ConfigSvr规格'),
      [MachineTypes.SQLSERVER_HA]: t('后端存储机型'),
      [MachineTypes.SQLSERVER_SINGLE]: t('后端存储机型'),
      [MachineTypes.PULSAR_BROKER]: t('Broker节点规格'),
      [MachineTypes.PULSAR_BOOKKEEPER]: t('Bookkeeper节点规格'),
      [MachineTypes.PULSAR_ZOOKEEPER]: t('Zookeeper节点规格'),
    };
    return this.spec_machine_type ? machineTypeMap[this.spec_machine_type] : '';
  }

  get sub_zone_detail_display() {
    return `${Object.entries(this.sub_zone_detail)
      .map(([zone, count]) => `${zone}: ${count}`)
      .join(', ')};`;
  }
}
