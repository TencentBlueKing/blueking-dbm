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

export default class SurrealSingleInstance {
  createdTime: string;
  instance_address: string;
  manifest: string; // json字符串
  node: string;
  podName: string;
  resourceQuota: {
    limitCpu: number;
    limitMemory: number;
    requestCpu: number;
    requestMemory: number;
    storage: number;
  };
  resourceUsage: {
    cpu: number;
    cpuPercent: number;
    memory: number;
    memoryPercent: number;
    storage: number;
    storagePercent: number;
  };
  status: string;

  constructor(payload = {} as SurrealSingleInstance) {
    this.createdTime = payload.createdTime || '';
    this.instance_address = payload.instance_address;
    this.manifest = payload.manifest;
    this.node = payload.node || '';
    this.podName = payload.podName || '';
    this.resourceQuota = payload.resourceQuota || {};
    this.resourceUsage = payload.resourceUsage || {};
    this.status = payload.status;
  }

  get createdTimeDisplay() {
    return utcDisplayTime(this.createdTime);
  }
}
