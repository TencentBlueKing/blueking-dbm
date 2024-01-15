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

export default class QuickSearchMachine {
  bk_biz_id: number;
  bk_city: number;
  bk_cloud_id: number;
  bk_host_id: number;
  cluster_domain: string;
  cluster_id: number;
  cluster_type: string;
  ip: string;
  spec_id: number;

  constructor(payload = {} as QuickSearchMachine) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_city = payload.bk_city;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_domain = payload.cluster_domain;
    this.cluster_id = payload.cluster_id;
    this.cluster_type = payload.cluster_type;
    this.ip = payload.ip;
    this.spec_id = payload.spec_id;
  }
}
