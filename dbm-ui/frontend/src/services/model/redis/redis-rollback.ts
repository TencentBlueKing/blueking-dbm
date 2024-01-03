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
export default class RedisRollback {
  // 0:未销毁 1:已销毁 2: 销毁中
  static NOT_DESTROYED = 0;
  static DESTROYING = 1;
  static DESTROYED = 2;

  app: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  creator: string;
  create_at: string;
  host_count: number;
  id: number;
  destroyed_status: number;
  prod_instance_range: string[];
  prod_temp_instance_pairs: string[][];
  prod_cluster_type: string;
  prod_cluster: string;
  prod_cluster_id: number;
  related_rollback_bill_id: number;
  recovery_time_point: string;
  specification: {
    id: number;
    cpu: {
      max: number;
      min: number;
    };
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    name: string;
    count: number;
    device_class: string[];
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[]
  };
  temp_instance_range: string[];
  temp_cluster_type: string;
  temp_cluster_proxy: string;
  updater: string;
  update_at: string;
  isShowInstancesTip: boolean;

  constructor(payload = {} as RedisRollback) {
    this.app = payload.app;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.host_count = payload.host_count;
    this.id = payload.id;
    this.destroyed_status = payload.destroyed_status;
    this.prod_instance_range = payload.prod_instance_range;
    this.prod_temp_instance_pairs = payload.prod_temp_instance_pairs;
    this.prod_cluster_type = payload.prod_cluster_type;
    this.prod_cluster = payload.prod_cluster;
    this.prod_cluster_id = payload.prod_cluster_id;
    this.related_rollback_bill_id = payload.related_rollback_bill_id;
    this.recovery_time_point = payload.recovery_time_point;
    this.specification = payload.specification;
    this.temp_instance_range = payload.temp_instance_range;
    this.temp_cluster_type = payload.temp_cluster_type;
    this.temp_cluster_proxy = payload.temp_cluster_proxy;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
    this.isShowInstancesTip = false;
  }

  get isNotDestroyed() {
    return this.destroyed_status === RedisRollback.NOT_DESTROYED;
  }

  get isDestroyed() {
    return this.destroyed_status === RedisRollback.DESTROYED;
  }

  get isDestroying() {
    return this.destroyed_status === RedisRollback.DESTROYING;
  }

  get recoveryTimePointDisplay() {
    return utcDisplayTime(this.recovery_time_point);
  }
}
