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
  <div class="task-item">
    <DbIcon
      :class="{ 'loading-flag': isRunning }"
      style="flex-shrink: 0"
      svg
      :type="isRunning ? 'sync-pending' : isFailed ? 'sync-failed' : 'sync-default'" />
    <div class="ml-4">
      <span>【{{ data.title }}】{{ t('单据ID') }}：</span>
      <span
        class="ticket-id"
        @click="() => handleClickRelatedTicket(data.ticket_id)">
        #{{ data.ticket_id }}
      </span>
      <span
        v-if="isFailed"
        class="fail-tip">
        &nbsp;,&nbsp;
        <span style="color: #ea3636">{{ $t('执行失败') }}</span>
        &nbsp;,&nbsp;{{ $t('待继续') }}
      </span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { PipelineStatus } from '@common/const';

  export interface Props {
    data: {
      cluster_id: number;
      flow_id: number;
      status: PipelineStatus;
      ticket_id: number;
      ticket_type: string;
      title: string;
    };
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();

  const isRunning = computed(() => props.data.status === PipelineStatus.RUNNING);
  const isFailed = computed(() => props.data.status === PipelineStatus.FAILED);

  const handleClickRelatedTicket = (billId: number) => {
    const route = router.resolve({
      name: 'bizTicketManage',
      query: {
        id: billId,
      },
    });
    window.open(route.href);
  };
</script>
<style lang="less" scoped>
  .task-item {
    display: flex;
    width: 100%;
    // height: 20px;
    padding: 4px 0;
    align-items: center;
    font-size: 12px;
    color: #63656e;

    .ticket-id {
      color: #3a84ff;
      cursor: pointer;
    }

    .loading-flag {
      display: flex;
      color: #3a84ff;
      animation: rotate-loading 1s linear infinite;
    }
  }
</style>
