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
import { semanticCheckResultLogs } from '@services/source/sqlImport';

export type IFileLogItem = ServiceReturnType<typeof semanticCheckResultLogs>[number];
export type ILogItem = IFileLogItem['match_logs'][number];

export default function (rootId: string, nodeId: string) {
  const isLoading = ref(false);
  const wholeLogList = shallowRef([] as ILogItem[]);
  const fileLogMap = shallowRef({} as Record<string, IFileLogItem>);

  let logTimer = 0;
  const fetchLog = () => {
    semanticCheckResultLogs({
      cluster_type: 'mysql',
      root_id: rootId,
      node_id: nodeId,
    })
      .then((logData) => {
        const wholeist: ILogItem[] = [];
        const fileMap: Record<string, IFileLogItem> = {};
        logData.forEach((logItem) => {
          wholeist.push(...logItem.match_logs);
          const filename = logItem.filename.replace(/[^_]+_/, '');
          fileMap[filename] = logItem;
        });

        wholeLogList.value = wholeist;
        fileLogMap.value = fileMap;

        logTimer = setTimeout(() => {
          fetchLog();
        }, 5000);
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  onMounted(() => {
    fetchLog();
  });

  onBeforeUnmount(() => {
    clearTimeout(logTimer);
  });
  return {
    isLoading,
    wholeLogList,
    fileLogMap,
  };
}
