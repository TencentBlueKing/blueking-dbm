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
import { type ComponentInternalInstance } from 'vue';

import { useGlobalBizs } from '@stores';

import { ClusterTypes } from '@common/const';

interface TopoTreeData {
  children: Array<TopoTreeData>;
  count: number;
  id: number;
  name: string;
  obj: 'biz' | 'cluster';
}

/**
 * 处理集群列表数据
 */
export function useTopoData<T extends Record<string, any>>(filterClusterId: ComputedRef<number | undefined>) {
  const { currentBizId, currentBizInfo } = useGlobalBizs();
  const currentInstance = getCurrentInstance() as {
    proxy: {
      countFunc?: (data: T) => number;
      getTopoList: (params: any) => Promise<any>;
      totalCountFunc?: (data: { ip: string }[]) => number;
    };
  } & ComponentInternalInstance;

  const isLoading = ref(false);
  const selectClusterId = ref<number>();
  const treeRef = ref();

  const treeData = shallowRef<TopoTreeData[]>([]);

  /**
   * 获取列表
   */
  const fetchResources = async () => {
    isLoading.value = true;
    const params = {
      bk_biz_id: currentBizId,
      cluster_type: ClusterTypes.REDIS_INSTANCE,
    } as Record<string, any>;
    return currentInstance.proxy
      .getTopoList(params)
      .then((data) => {
        const countFn = currentInstance.proxy?.countFunc;
        const formatData = data.map((item: T) => ({ ...item, count: countFn ? countFn(item) : item.masters.length }));
        const children = formatData.map((item: T) => ({
          children: [],
          count: item.count,
          id: item.id,
          name: item.master_domain,
          obj: 'cluster',
        }));
        const totalCountFunc = currentInstance.proxy?.totalCountFunc;
        treeData.value = filterClusterId.value
          ? children
          : [
              {
                children,
                count: totalCountFunc
                  ? totalCountFunc(data)
                  : formatData.reduce((count: number, item: any) => count + item.count, 0),
                id: currentBizId,
                name: currentBizInfo?.display_name || '--',
                obj: 'biz',
              },
            ];
        setTimeout(() => {
          if (data.length > 0) {
            const [firstNode] = treeData.value;
            selectClusterId.value = firstNode.id;
            const [firstRawNode] = treeRef.value.getData().data;
            treeRef.value.setOpen(firstRawNode);
            treeRef.value.setSelect(firstRawNode);
          }
        });
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  return {
    fetchResources,
    isLoading,
    selectClusterId,
    treeData,
    treeRef,
  };
}
