<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div v-if="(taskCount <= 0)" />
  <div v-else>
    <div
      ref="rootRef"
      class="task-count">
      <DbStatus theme="loading" />
      <strong>{{ taskCount }}</strong>
    </div>
    <div
      ref="popRef"
      class="sql-execute-task-popover-list">
      <div
        v-for="item in taskList"
        :key="item.root_id"
        class="task-item">
        <div>
          <DbIcon
            v-if="item.isPending"
            type="loading" />
          <DbIcon
            v-else-if="item.isSucceeded"
            style="color: #2dcb56;"
            type="check-circle-fill" />
          <DbIcon
            v-else
            style="color: #ea3636;"
            type="delete-fill" />
        </div>
        <div class="task-create-time">
          {{ item.created_at }}
        </div>
        <div class="task-create-action">
          <BkPopover>
            <DbIcon
              type="delete"
              @click="handleRevokeTask(item)" />
            <template #content>
              <span>{{ $t('移除') }}</span>
            </template>
          </BkPopover>
          <BkPopover>
            <DbIcon
              class="ml8"
              type="link"
              @click="handleGoTaskLog(item)" />
            <template #content>
              <span>{{ $t('执行日志') }}</span>
            </template>
          </BkPopover>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import DbStatus from '@components/db-status/index.vue';

  import { useTaskCount } from '@/views/mysql/common/hooks/useTaskCount';

  const {
    rootRef,
    popRef,
    taskList,
    taskCount,
    handleRevokeTask,
    handleGoTaskLog,
  } = useTaskCount();
</script>
<style lang="less" scoped>
.task-count {
  height: 16px;
  padding-right: 8px;
  padding-left: 4px;
  margin-left: 4px;
  font-size: 12px;
  line-height: 16px;
  color: @primary-color;
  background-color: white;
  border-radius: 20px;

  :deep(.bk-loading-size-mini) {
    margin-right: 0;
  }

  :deep(.db-status) {
    margin-top: -2px;
    transform: scale(0.6);
  }
}

.sql-execute-task-popover-list {
  max-height: 280px;
  padding: 12px 16px 12px 12px;
  margin: -5px -9px;
  overflow: auto;
  font-size: 12px;
  line-height: 24px;
  color: #63656e;

  .task-item {
    display: flex;
    align-items: center;
    height: 24px;

    &:hover {
      color: #3a84ff;
    }
  }

  .task-create-time {
    padding-right: 16px;
    padding-left: 8px;
  }

  .task-create-action {
    display: flex;
    font-size: 12px;
    color: #3a84ff;
    align-items: center;

    & > * {
      cursor: pointer;
    }
  }
}
</style>
