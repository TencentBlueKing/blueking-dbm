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

import dayjs from 'dayjs';

import { t } from '@locales/index';

export default class RiakNode {
  static NORMAL = 'normal';
  static ABNORMAL = 'abnormal';
  static DELETING = 'DELETING';
  static REBOOTING = 'REBOOTING';

  static labelMap: Record<string, string> = {
    [RiakNode.DELETING]: 'shanchuzhong',
    [RiakNode.REBOOTING]: 'zhongqizhong',
  };

  static keyPathMap: Record<string, string> = {
    [RiakNode.DELETING]: '删除任务正在进行中，跳转xx查看进度',
    [RiakNode.REBOOTING]: '重启任务正在进行中，跳转xx查看进度',
  };

  static stautsInfo: Record<string, {
    theme: string,
    text: string
  }> = {
      [RiakNode.NORMAL]: {
        theme: 'success',
        text: t('正常'),
      },
      [RiakNode.ABNORMAL]: {
        theme: 'danger',
        text: t('异常'),
      },
    };

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_host_name: string;
  cpu: number;
  create_at: string;
  disk: number;
  ip: string;
  machine_type: string;
  mem: number;
  node_count: number;
  role: string;
  status: number;

  constructor(payload = {} as RiakNode) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_name = payload.bk_host_name;
    this.cpu = payload.cpu;
    this.create_at = payload.create_at;
    this.disk = payload.disk;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.mem = payload.mem;
    this.node_count = payload.node_count;
    this.role = payload.role;
    this.status = payload.status;
  }

  get isNewRow() {
    if (!this.create_at) {
      return '';
    }

    const createDay = dayjs(this.create_at);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  }

  get isNodeNormal() {
    return this.status !== 0;
  }

  // get getCpuInfo() {
  //   let rate = 0;
  //   let color = '#2DCB56';

  //   if (this.cpu_total !== 0) {
  //     rate = Math.round(this.cpu_used / this.cpu_total * 100);
  //   }

  //   if (rate >= 90) {
  //     color = '#EA3636';
  //   } else if (rate >= 70) {
  //     color = '#FF9C01';
  //   }

  //   return {
  //     percent: rate,
  //     rate: `${rate.toFixed(2)}%`,
  //     num: `(${this.cpu_used}G/${this.cpu_total}G)`,
  //     color,
  //   };
  // }
}

