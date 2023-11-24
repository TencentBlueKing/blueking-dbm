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
  getNodeLog,
  getRetryNodeHistories,
} from '@services/source/taskflow';

export type ILogItem = ServiceReturnType<typeof getNodeLog>[number]

/**
 * 计算执行文件成功、失败个数
 */
export default function () {
  let versionId = '';
  const isLoading = ref(false);
  const wholeLogList = shallowRef([] as ILogItem[]);
  const fileStartReg = /.*\[start\]-(.+)$/;
  const fileEndReg = /.*\[end\]-(.+)$/;
  const counts = reactive({
    success: 0,
    fail: 0,
  });

  let lastLogLength = 0;
  let logTimer = 0;
  const fetchLog = (rootId: string, nodeId: string) => {
    getNodeLog({
      version_id: versionId,
      root_id: rootId,
      node_id: nodeId,
    }).then((logData) => {
      if (lastLogLength !== logData.length) {
        wholeLogList.value = logData as ILogItem[];
      }
      lastLogLength = logData.length;

      if (logTimer < 0) {
        return;
      }
      logTimer = setTimeout(() => {
        fetchLog(rootId, nodeId);
      }, 2000);
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

  let versionTimer = 0;
  const fetchVersion = (rootId: string, nodeId: string) => {
    isLoading.value = true;
    getRetryNodeHistories({
      root_id: rootId,
      node_id: nodeId,
    }).then((data) => {
      if (data.length > 0 && data[0].version) {
        versionId = data[0].version;
        fetchLog(rootId, nodeId);
        clearTimeout(versionTimer);
        return;
      }

      if (versionTimer < 0) {
        return;
      }
      versionTimer = setTimeout(() => {
        fetchVersion(rootId, nodeId);
      }, 2000);
    })
      .catch(() => {
        isLoading.value = false;
      });
  };

  watch(() => wholeLogList, () => {
    const successLogs: any[] = [];
    const failLogs: any[] = [];
    wholeLogList.value.forEach((item) => {
      if (item.message.match(fileStartReg)) {
        successLogs.push(item);
      }
      if (item.message.match(fileEndReg)) {
        failLogs.push(item);
      }
    });
    const diffCounts = successLogs.length - failLogs.length;
    counts.success =  successLogs.length - diffCounts;
    counts.fail =  diffCounts === 0 ? 0 : diffCounts;
  }, { immediate: true, deep: true });


  onBeforeUnmount(() => {
    clearTimeout(logTimer);
    clearTimeout(versionTimer);
    logTimer = -1;
    versionTimer = -1;
  });

  return {
    counts,
    fetchVersion,
  };
}
