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
  <div style="margin-bottom: 40px;">
    <BkAlert
      v-if="(taskCount < 1)"
      closable
      theme="info"
      :title="t('提供多个集群批量执行sql文件功能')" />
    <div v-else>
      <BkAlert
        :show-icon="false"
        theme="warning">
        <div class="sql-execute-task-tips">
          <div
            class="loading-flag rotate-loading"
            style="width: 12px; height: 12px;">
            <DbIcon
              svg
              type="sync-pending" />
          </div>
          <div style="padding-left: 4px;">
            <span>{{ t('目前已有') }}</span>
            <span
              ref="rootRef"
              class="strong-number">{{ taskCount }}</span>
            <span>{{ t('个模拟执行任务待确认_可点击查看最新动态') }}</span>
          </div>
        </div>
      </BkAlert>
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
            <div
              v-bk-tooltips="t('移除')"
              @click="handleRevokeTask(item)">
              <DbIcon type="delete" />
            </div>
            <div
              v-bk-tooltips="t('执行日志')"
              @click="handleGoTaskLog(item)">
              <DbIcon
                class="ml8"
                type="link" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useTaskCount } from '@/views/mysql/common/hooks/useTaskCount';

  const { t } = useI18n();
  const {
    rootRef,
    popRef,
    taskList,
    taskCount,
    handleRevokeTask,
    handleGoTaskLog,
  } = useTaskCount('tendbcluster');
</script>
<style lang="less">
  .sql-execute-task-tips {
    display: flex;
    align-items: center;

    .loading-flag {
      display: flex;
      width: 12px;
      height: 12px;
      align-items: center;
      justify-self: center;
    }

    .strong-number {
      padding: 0 4px;
      font-weight: bold;
      color: #3a84ff;
      cursor: pointer;
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
