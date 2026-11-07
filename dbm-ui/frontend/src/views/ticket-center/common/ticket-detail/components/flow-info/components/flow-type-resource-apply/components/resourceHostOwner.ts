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

import { useGlobalBizs } from '@stores';

import type { IResouce } from './ResourceDetailHostTable.vue';

/**
 * 取主机的资源归属（所属业务、资源标签、所属DB），页面展示与导出共用
 */
export const getResourceHostOwnerData = (data: IResouce) => {
  if (data.for_biz_info) {
    return {
      for_biz: data.for_biz_info,
      labels: data.label_info,
      resource_type: data.resource_type,
    };
  }

  const baseData = {
    labels: [],
    resource_type: data.resource_type,
  };
  // 兼容历史单据数据结构
  if (typeof data.for_biz === 'number') {
    return {
      ...baseData,
      for_biz: {
        bk_biz_id: data.for_biz,
        bk_biz_name: useGlobalBizs().bizIdMap.get(data.for_biz)?.display_name || '--',
      },
    };
  }

  return {
    ...baseData,
    for_biz: data.for_biz,
  };
};
