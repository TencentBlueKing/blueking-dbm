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

interface Config{
  label: string,
  component: string,
  flex?: number,
}

export default {
  for_bizs: {
    label: '专用业务',
    component: 'for_bizs',
  },
  resource_types: {
    label: '专用 DB',
    component: 'resource_types',
  },
  hosts: {
    label: 'IP',
    component: 'hosts',
    flex: 2,
  },
  agent_status: {
    label: 'Agent 状态',
    component: 'agent_status',
  },
  city: {
    label: '城市',
    component: 'city',
  },
  subzones: {
    label: '园区',
    component: 'subzones',
  },
  device_class: {
    label: '机型',
    component: 'device_class',
  },
  mount_point: {
    label: '磁盘挂载点',
    component: 'mount_point',
  },
  cpu: {
    label: 'CPU(核)',
    component: 'cpu',
  },
  mem: {
    label: '内存(G)',
    component: 'mem',
  },
  disk: {
    label: '磁盘(G)',
    component: 'disk',
  },
  disk_type: {
    label: '磁盘类型',
    component: 'disk_type',
  },
} as Record<string, Config>;
