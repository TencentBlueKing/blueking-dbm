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

import { getLevelConfig } from '@services/source/configs';

import { clusterTypeInfos, ClusterTypes, ConfLevels, DBTypes } from '@common/const';

import { notModuleClusters } from '@views/db-configure/common/const';

import type { TreeData } from '../types';

type LevelConfigDetail = { charset?: string } & ServiceReturnType<typeof getLevelConfig>;

interface State {
  data: LevelConfigDetail;
  deployInfo: LevelConfigDetail;
  isEmpty: boolean;
  loading: boolean;
  loadingDetails: boolean;
  version: string;
}
/**
 * 获取参数管理基本信息
 */
export const useBaseDetails = (immediateFetch = true, confName = 'db_version') => {
  const getFetchParams = (versionKey: 'version' | 'proxy_version', confType = 'dbconf') => {
    if (treeNode === undefined) {
      return {} as ServiceParameters<typeof getLevelConfig>;
    }

    const { data, id, levelType, parentId } = treeNode.value;
    const notExistModule = notModuleClusters.includes(dbType.value);
    const params = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      conf_type: confType,
      level_info: undefined as any,
      level_name: levelType,
      level_value: id,
      meta_cluster_type: clusterType.value,
      version: state.version || data?.extra?.[versionKey],
    };
    if (parentId && levelType === ConfLevels.CLUSTER) {
      let [parentLevelType, parentNodeId] = parentId.split('-');
      if (notExistModule) {
        parentLevelType = 'module';
        parentNodeId = '0';
      }
      params.level_info = {
        [parentLevelType]: parentNodeId,
      };
    }
    return params;
  };

  const treeNode = inject<ComputedRef<TreeData>>('treeNode');
  const route = useRoute();
  const clusterType = computed(() => (route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);
  const dbType = computed(() => clusterTypeInfos[clusterType.value].dbType);
  const state = reactive<State>({
    data: {
      charset: '',
      conf_items: [],
      description: '',
      name: '',
      version: '',
    },
    deployInfo: {
      charset: '',
      conf_items: [],
      description: '',
      name: '',
      version: '',
    },
    isEmpty: false,
    loading: false,
    loadingDetails: false,
    version: '',
  });

  const fetchParams = computed(() => getFetchParams('version'));

  /**
   * 查询配置详情
   */
  const fetchLevelConfig = () => {
    state.loadingDetails = true;
    getLevelConfig(fetchParams.value)
      .then((res) => {
        state.data = {
          ...state.data,
          ...res,
        };
      })
      .finally(() => {
        state.loadingDetails = false;
      });
  };

  /**
   * 获取绑定模块信息
   */
  const fetchModuleConfig = (moduleId: number) => {
    const params = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      conf_type: 'deploy',
      level_name: 'module',
      level_value: moduleId,
      meta_cluster_type: clusterType.value,
      version: 'deploy_info',
    };

    state.loading = true;
    getLevelConfig(params)
      .then((result) => {
        state.deployInfo = result;
        result.conf_items.forEach((item) => {
          if (item.conf_name === confName) {
            state.version = item.conf_value ?? '';
          } else if (item.conf_name === 'charset') {
            state.data.charset = item.conf_value ?? '';
          }
        });
        if (state.version) {
          fetchLevelConfig();
        } else {
          state.isEmpty = true;
        }
      })
      .finally(() => {
        state.loading = false;
      });
  };

  watch(
    () => treeNode,
    (node, old) => {
      if (immediateFetch && node && node.value.treeId !== old?.value?.treeId) {
        let { id } = node.value;
        if (node.value.levelType === ConfLevels.CLUSTER && node.value.parentId) {
          const parentInfo = (node.value.parentId as string).split('-');
          id = Number(parentInfo[1]);
        }
        if ([DBTypes.MYSQL, DBTypes.SQLSERVER, DBTypes.TENDBCLUSTER].includes(dbType.value)) {
          fetchModuleConfig(id);
        } else if (notModuleClusters.includes(dbType.value)) {
          fetchLevelConfig();
        }
      }
    },
    { deep: true, immediate: true },
  );

  return {
    dbType,
    fetchParams,
    getFetchParams,
    state,
  };
};
