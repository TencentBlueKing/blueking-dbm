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

export default class RedisDtsServiceStatus {
  bk_city_name: string;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  status: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as RedisDtsServiceStatus) {
    this.ip = payload.ip;
    this.status = payload.status;
    this.bk_host_id = payload.bk_host_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.bk_city_name = payload.bk_city_name;
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
