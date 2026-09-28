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

import { getNodeLog, getRetryNodeHistories } from '@services/source/taskflow';

import { useFetchAllPages } from '@hooks';

/**
 * 计算执行文件成功、失败个数
 */
export default function () {
  let versionId = '';
  const isLoading = ref(false);
  // 统计依赖全量日志，按分片取全量
  const { data: wholeLogList, runAsync: fetchWholeLogList } = useFetchAllPages(getNodeLog);
  const fileStartReg = /.*\[start\]-(.+)$/;
  const fileEndReg = /.*\[end\]-(.+)$/;
  const counts = reactive({
    fail: 0,
    success: 0,
  });

  let logTimer: NodeJS.Timeout;

  const fetchLog = (rootId: string, nodeId: string) => {
    fetchWholeLogList({
      node_id: nodeId,
      root_id: rootId,
      version_id: versionId,
    })
      .then(() => {
        logTimer = setTimeout(() => {
          fetchLog(rootId, nodeId);
        }, 2000);
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  let versionTimer: NodeJS.Timeout;
  const fetchVersion = (rootId: string, nodeId: string) => {
    isLoading.value = true;
    getRetryNodeHistories({
      node_id: nodeId,
      root_id: rootId,
    })
      .then((data) => {
        if (data.length > 0 && data[0].version) {
          versionId = data[0].version;
          fetchLog(rootId, nodeId);
          clearTimeout(versionTimer);
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

  watch(
    () => wholeLogList,
    () => {
      const successLogs: any[] = [];
      const failLogs: any[] = [];
      wholeLogList.value.forEach((item) => {
        const message = item.message.slice(0, 300);
        if (message.match(fileStartReg)) {
          successLogs.push(item);
        }
        if (message.match(fileEndReg)) {
          failLogs.push(item);
        }
      });
      const diffCounts = successLogs.length - failLogs.length;
      counts.success = successLogs.length - diffCounts;
      counts.fail = diffCounts === 0 ? 0 : diffCounts;
    },
    {
      deep: true,
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    clearTimeout(logTimer);
    clearTimeout(versionTimer);
  });

  return {
    counts,
    fetchVersion,
  };
}
