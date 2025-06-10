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

export default class DbhaServiceStatus {
  bk_city_name: string;
  bk_cloud_id: number;
  city_id: number;
  db_type: string;
  ip: string;
  last_time: string;
  module: string;
  port: number;
  report_interval: number;
  start_time: string;
  status: string;
  uid: number;

  constructor(payload = {} as DbhaServiceStatus) {
    this.bk_city_name = payload.bk_city_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.city_id = payload.city_id;
    this.db_type = payload.db_type;
    this.ip = payload.ip;
    this.last_time = payload.last_time;
    this.module = payload.module;
    this.port = payload.port;
    this.report_interval = payload.report_interval;
    this.start_time = payload.start_time;
    this.status = payload.status;
    this.uid = payload.uid;
  }

  get lastTimeDisplay() {
    return utcDisplayTime(this.last_time) || '--';
  }

  get startTimeDisplay() {
    return utcDisplayTime(this.start_time) || '--';
  }

  get statusInfo() {
    return (
      clusterInstStatus[this.status as ClusterInstStatusKeys] || clusterInstStatus[ClusterInstStatusKeys.UNAVAILABLE]
    );
  }
}
