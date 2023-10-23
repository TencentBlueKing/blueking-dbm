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
import {
  type ComponentInternalInstance,
  getCurrentInstance,
  reactive,
  type Ref,
  ref,
  shallowRef,
} from 'vue';

import { useGlobalBizs } from '@stores';

interface TopoTreeData {
  id: number;
  name: string;
  obj: 'biz' | 'cluster',
  count: number,
  children: Array<TopoTreeData>;
}

/**
 * 处理集群列表数据
 */
export function useTopoData(activePanel?: Ref<string>) {
  const { currentBizId, currentBizInfo } = useGlobalBizs();
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getTopoList: (params: any) => Promise<any>
    }
  };

  const isLoading = ref(false);
  const treeData = shallowRef<TopoTreeData[]>([]);
  const selectClusterId = ref<number>();

  /**
   * 获取列表
   */
  const fetchResources = async () => {
    isLoading.value = true;
    return currentInstance.proxy.getTopoList({
      bk_biz_id: currentBizId,
      cluster_filters: [
        {
          bk_biz_id: currentBizId,
          cluster_type: activePanel?.value,
        },
      ],
    }).then((data) => {
      const formatData = data.map((item: any) => ({ ...item, count: item.remote_db.length }));
      treeData.value = [
        {
          name: currentBizInfo?.display_name || '--',
          id: currentBizId,
          obj: 'biz',
          count: formatData.reduce((count: number, item: any) => count + item.count, 0),
          children: formatData.map((item: any) => ({
            id: item.id,
            name: item.cluster_name,
            obj: 'cluster',
            count: item.count,
            children: [],
          })),
        },
      ];
      setTimeout(() => {
        if (data.length > 0) {
          const [firstNode] = treeData.value;
          selectClusterId.value = firstNode.id;
        }
      });
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  return {
    isLoading,
    treeData,
    selectClusterId,
    fetchResources,
  };
}
