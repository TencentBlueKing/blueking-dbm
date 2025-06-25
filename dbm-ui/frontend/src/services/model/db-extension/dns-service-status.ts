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

import { clusterInstStatus, ClusterInstStatusKeys } from '@common/const';

import { utcDisplayTime } from '@utils';

import { t } from '@/locales';

export default class DnsServiceStatus {
  bk_city: string;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  is_access: boolean;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as DnsServiceStatus) {
    this.ip = payload.ip;
    this.status = payload.status;
    this.bk_host_id = payload.bk_host_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.bk_city = payload.bk_city;
    this.is_access = payload.is_access;
  }

  get isAccessDisplay() {
    return this.is_access ? t('是') : t('否');
  }

  get statusInfo() {
    return (
      clusterInstStatus[this.status as ClusterInstStatusKeys] || clusterInstStatus[ClusterInstStatusKeys.UNAVAILABLE]
    );
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at) || '--';
  }
}
