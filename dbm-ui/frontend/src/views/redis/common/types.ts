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
import RedisModel from '@services/model/redis/redis';

import type { IPagination } from '@hooks';

/**
 * redis 集群列表基础数据类型
 */
export interface RedisState {
  isInit: boolean,
  isAnomalies: boolean,
  isLoading: boolean,
  data: RedisModel[],
  selected: RedisModel[],
  searchValues: {
    id: string,
    name: string,
    values: {
      id: string,
      name: string,
    }[]
  }[],
  pagination: IPagination,
}


export enum AffinityType {
  SAME_SUBZONE_CROSS_SWTICH = 'SAME_SUBZONE_CROSS_SWTICH', // 同城同subzone跨交换机跨机架
  SAME_SUBZONE = 'SAME_SUBZONE', // 同城同subzone
  CROS_SUBZONE = 'CROS_SUBZONE', // 同城跨subzone
  NONE = 'NONE', // 无需亲和性处理
}
