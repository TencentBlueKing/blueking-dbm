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
  onBeforeUnmount,
  ref,
  shallowRef,
} from 'vue';

import {
  getNodeLog,
  getRetryNodeHistories,
} from '@services/source/taskflow';

export type ILogItem = ServiceReturnType<typeof getNodeLog>[number]

export const parseLog = (list: ILogItem[]) => {
  const fileStartReg = /.*\[start\]-(.+)$/;
  const fileEndRef = /.*\[end\]-(.+)$/;
  const fileLogMap = {} as Record<string, ILogItem[]>;

  let fileStart = false;
  let fileName = '';

  list.forEach((item) => {
    const fileStartCheck = item.message.match(fileStartReg);
    if (fileStartCheck) {
      fileStart = true;
      fileName = fileStartCheck[1].replace(/[^_]+_/, '');
      fileLogMap[fileName] = [];
      return;
    }

    const fileEndCheck = item.message.match(fileEndRef);
    if (fileEndCheck) {
      fileStart = false;
      return;
    }
    if (fileStart) {
      fileLogMap[fileName].push(item);
    }
  });
  return fileLogMap;
};


export default function (rootId: string, nodeId: string) {
  let versionId = '';
  const isLoading = ref(false);
  const wholeLogList = shallowRef([] as ILogItem[]);
  const fileLogMap = shallowRef({} as Record<string, ILogItem[]>);

  let lastLogLength = 0;
  let logTimer = 0;
  const fetchLog = () => {
    getNodeLog({
      version_id: versionId,
      root_id: rootId as string,
      node_id: nodeId as string,
    }).then((logData) => {
      if (lastLogLength !== logData.length) {
        wholeLogList.value = logData as ILogItem[];
        fileLogMap.value = parseLog(logData);
      }
      lastLogLength = logData.length;

      if (logTimer < 0) {
        return;
      }
      logTimer = setTimeout(() => {
        fetchLog();
      }, 2000);
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  let versionTimer = 0;
  const fetchVersion = () => {
    isLoading.value = true;
    getRetryNodeHistories({
      root_id: rootId,
      node_id: nodeId,
    }).then((data) => {
      if (data.length > 0 && data[0].version) {
        versionId = data[0].version;
        fetchLog();
        clearTimeout(versionTimer);
        return;
      }

      if (versionTimer < 0) {
        return;
      }
      versionTimer = setTimeout(() => {
        fetchVersion();
      }, 2000);
    })
      .catch(() => {
        isLoading.value = false;
      });
  };

  fetchVersion();

  onBeforeUnmount(() => {
    logTimer = -1;
    versionTimer = -1;
  });
  return {
    isLoading,
    wholeLogList,
    fileLogMap,
  };
}
