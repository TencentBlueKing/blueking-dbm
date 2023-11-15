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
import type { ComponentInternalInstance } from 'vue';

import type { RowData } from './Index.vue';

export function useDetailData<T extends Record<string, any>>() {
  const currentInstance = getCurrentInstance() as ComponentInternalInstance & {
    proxy: {
      getDetailInfo: (params: any) => Promise<any>
    }
  };

  const isLoading = ref(false);
  const clusterId = ref();
  const tableData = ref<RowData[]>([]);

  const fetchResources = async () => {
    isLoading.value = true;
    return currentInstance.proxy.getDetailInfo({
      id: clusterId.value,
    })
      .then((res: T) => {
        tableData.value = res.cluster_entry_details.map((item: {
          cluster_entry_type: string;
          entry: string;
          target_details: { ip: string, port: number }[];
        }) => ({
          type: item.cluster_entry_type,
          entry: item.entry,
          ips: item.target_details.map(row => row.ip).join('\n'),
          port: item.target_details[0].port,
        }));
      })
      .catch(() => {
        tableData.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };


  return {
    isLoading,
    clusterId,
    data: tableData,
    fetchResources,
  };
}
