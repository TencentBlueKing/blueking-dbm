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
import type { ListBase } from '@services/types';

import http from '../http';

const path = '/apis/monitor/subscribe';

/**
 * 告警订阅删除
 */
export function deleteSubscribe(params: { ids: number[] }) {
  return http.post<null>(`${path}/delete_subscribe/`, params);
}

/**
 * 获取告警订阅指标
 */
export function getSubscribeMetrics(params?: { limit?: number; offset?: number }) {
  return http.get<
    Record<
      string,
      {
        id: string;
        name: string;
      }[]
    >
  >(`${path}/get_subscribe_metrics/`, params);
}

/**
 * 告警订阅列表
 */
export function getSubscribeList() {
  return http.get<
    ListBase<
      {
        alert_severity: number[];
        bk_biz_id: number;
        cluster_id: string;
        cluster_name: string;
        cluster_type: string;
        conditions: {
          condition: string;
          field: string;
          method: string;
          value: (string | number)[];
        }[];
        db_type: string;
        id: number;
        is_enable: boolean;
        master_domain: string;
        notice_ways: string[];
        priority: number;
        user_type: string;
        username: string;
      }[]
    >
  >(`${path}/list_subscribe/`);
}

/**
 * 保存告警订阅
 */
export function saveSubscribe(params: {
  alert_level: number[];
  clusters: {
    cluster_domain: string;
    cluster_type: string;
  }[];
  notice_ways: string[];
}) {
  return http.post<null>(`${path}/save_subscribe/`, params);
}
