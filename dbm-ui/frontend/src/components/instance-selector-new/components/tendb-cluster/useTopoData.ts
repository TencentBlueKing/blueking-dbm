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

import { activePanelInjectionKey } from '@components/instance-selector-new/Index.vue';

interface TopoTreeData {
  id: number;
  name: string;
  obj: 'biz' | 'cluster';
  count: number;
  children: Array<TopoTreeData>;
}

/**
 * 处理集群列表数据
 */
export function useTopoData<T extends Record<string, any>>(filterClusterId: ComputedRef<number | undefined>) {
  const { currentBizId, currentBizInfo } = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getTopoList: (params: any) => Promise<any>;
      countFunc?: (data: T) => number;
    };
  };

  const activePanel = inject(activePanelInjectionKey) as Ref<string> | undefined;

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
      cluster_filters: [
        {
          bk_biz_id: currentBizId,
          cluster_type: activePanel?.value,
        },
      ],
    } as Record<string, any>;
    if (filterClusterId.value) {
      params.cluster_filters[0].id = filterClusterId.value;
    }
    return currentInstance.proxy
      .getTopoList(params)
      .then((data) => {
        const countFn = currentInstance.proxy?.countFunc;
        const formatData = data.map((item: T) => ({ ...item, count: countFn ? countFn(item) : item.remote_db.length }));
        const children = formatData.map((item: T) => ({
          id: item.id,
          name: item.master_domain,
          obj: 'cluster',
          count: item.count,
          children: [],
        }));
        treeData.value = filterClusterId.value
          ? children
          : [
              {
                name: currentBizInfo?.display_name || '--',
                id: currentBizId,
                obj: 'biz',
                count: formatData.reduce((count: number, item: any) => count + item.count, 0),
                children,
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
    treeRef,
    isLoading,
    treeData,
    selectClusterId,
    fetchResources,
  };
}
