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
import http from '@services/http';
import MonitorPolicyModel from '@services/model/monitor-policy/monitor-policy';

import { useGlobalBizs } from '@stores';

// import type { InstanceInfos } from './types/clusters';
// import type { ListBase } from './types/common';


// 获取策略列表
export const queryMonitorPolicyList = (params: {
  bk_biz_id?: number,
  db_type?: string,
  limit?: number,
  offset?: number,
}) => {
  const { currentBizId } = useGlobalBizs();
  Object.assign(params, {
    bk_biz_id: currentBizId,
  });
  return http.get<MonitorPolicyModel[]>('/apis/monitor/policy/', params);
};
