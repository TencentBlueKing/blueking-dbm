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

import http from '../http';

/**
 * 获取监控警告管理地址
 */
export function getMonitorUrls(params: Record<string, any> & {
  cluster_type: string,
  cluster_id?: number,
  instance_id?: number,
}) {
  return http.get<{
    urls: {
      url: string,
      view: string
    }[]
  }>('/apis/monitor/grafana/get_dashboard/', params);
}
