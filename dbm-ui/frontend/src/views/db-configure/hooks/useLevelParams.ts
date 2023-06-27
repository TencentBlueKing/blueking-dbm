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

import type { ComputedRef } from 'vue';

import { useGlobalBizs } from '@stores';

import {
  clusterTypeInfos,
  type ClusterTypesValues,
  ConfLevels,
  type ConfLevelValues,
} from '@common/const';

import { notModuleClusters } from '../common/const';

export type LevelParams = {
  level_name?: ConfLevelValues,
  level_value?: number,
  level_info?: any,
  bk_biz_id?: number
};

/**
 * 获取层级相关参数
 */
export const useLevelParams = (isPlat: boolean): ComputedRef<LevelParams> => {
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  return computed(() => {
    // 平台层级不需要额外参数
    if (isPlat) return {};

    const { treeId, parentId, clusterType } = route.params;
    if (!treeId) return {
      bk_biz_id: globalBizsStore.currentBizId,
    };

    const params = {
      level_name: ConfLevels.PLAT,
      level_value: 0,
      level_info: undefined as any,
      bk_biz_id: globalBizsStore.currentBizId,
    };
    // 处理路由参数
    const [levelType, nodeId] = (treeId as string).split('-');
    params.level_name = levelType as ConfLevels;
    params.level_value = Number(nodeId);
    const notExistModule = notModuleClusters.includes(clusterTypeInfos[clusterType as ClusterTypesValues].dbType);
    if (parentId && levelType === ConfLevels.CLUSTER) {
      let [parentLevelType, parentNodeId] = (parentId as string).split('-');
      if (notExistModule) {
        parentLevelType = 'module';
        parentNodeId = '0';
      }
      params.level_info = {
        [parentLevelType]: parentNodeId,
      };
    }
    return params;
  });
};
