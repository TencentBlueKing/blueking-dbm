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

import tippy, { type Instance, type SingleTarget } from 'tippy.js';
import { useRouter } from 'vue-router';

import type UserSemanticTaskModel from '@services/model/sql-import/user-semantic-task';
import { deleteUserSemanticTasks, getUserSemanticTasks } from '@services/source/sqlImport';

import { useGlobalBizs, useSQLTaskCount } from '@stores';

import { useTimeoutPoll } from '@vueuse/core';

export const useTaskCount = (clusterType: string) => {
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const taskCountStore = useSQLTaskCount();

  const rootRef = ref();
  const popRef = ref();
  const taskList = computed(() => taskCountStore.taskList);
  const taskCount = computed(() => taskCountStore.taskCount);

  let tippyIns: Instance | undefined;

  const destroyPopover = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  };

  const initPopover = () => {
    if (rootRef.value && !tippyIns) {
      tippyIns = tippy(rootRef.value as SingleTarget, {
        content: popRef.value,
        placement: 'right',
        appendTo: () => document.body,
        theme: 'light',
        maxWidth: 'none',
        trigger: 'mouseenter click',
        interactive: true,
        arrow: true,
        offset: [0, 8],
        zIndex: 999,
        hideOnClick: true,
      });
    }
  };

  const fetchData = () => {
    getUserSemanticTasks({
      bk_biz_id: currentBizId,
      cluster_type: clusterType,
    }).then((data) => {
      if (taskCountStore.isPolling === false) {
        resume();
        taskCountStore.isPolling = true;
      }

      taskCountStore.taskList = data;
      nextTick(() => {
        initPopover();
      });
    });
  };

  fetchData();

  const { pause, resume } = useTimeoutPoll(fetchData, 10000);

  watch(
    () => taskCountStore.isPolling,
    () => {
      if (taskCountStore.isPolling === false) {
        fetchData();
      }
    },
  );

  const handleRevokeTask = (taskData: UserSemanticTaskModel) => {
    deleteUserSemanticTasks({
      bk_biz_id: currentBizId,
      task_ids: [taskData.root_id],
      cluster_type: clusterType,
    }).then(() => {
      fetchData();
    });
  };

  const handleGoTaskLog = (taskData: UserSemanticTaskModel) => {
    router.push({
      name: clusterType === 'mysql' ? 'MySQLExecute' : 'spiderSqlExecute',
      params: {
        step: 'log',
      },
      query: {
        rootId: taskData.root_id,
        nodeId: taskData.node_id,
      },
    });
  };

  onBeforeUnmount(() => {
    pause();
    destroyPopover();
    taskCountStore.$reset();
  });

  return {
    rootRef,
    popRef,
    taskList,
    taskCount,
    handleRevokeTask,
    handleGoTaskLog,
  };
};
