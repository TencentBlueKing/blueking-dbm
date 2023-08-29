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
  <div class="item">
    <DbIcon
      :class="{ 'loading-flag': isRunning }"
      svg
      :type="isRunning ? 'sync-pending' : isFailed ? 'sync-failed' : 'sync-default'" />
    <span>【{{ data.title }}】{{ $t('单据ID') }}：</span>
    <span style="color:#3A84FF">#{{ data.ticket_id }}</span>
    <div
      v-if="isFailed"
      class="fail-tip">
      &nbsp;,&nbsp;<span style="color:#EA3636">{{ $t('执行失败') }}</span>&nbsp;,&nbsp;{{ $t('待确认') }}
    </div>
  </div>
</template>
<script setup lang="ts">

  import { PipelineStatus } from '@common/const';

  interface Props {
    data: {
      cluster_id: number;
      flow_id: number;
      status: PipelineStatus;
      ticket_id: number;
      ticket_type: string;
      title: string;
    }
  }

  const props = defineProps<Props>();

  const isRunning = computed(() => props.data.status === PipelineStatus.RUNNING);
  const isFailed = computed(() => props.data.status === PipelineStatus.FAILED);

</script>
<style lang="less" scoped>
  .item {
    display: flex;
    width: 100%;
    height: 20px;
    align-items: center;
    font-size: 12px;
    color: #63656E;

    .loading-flag {
      display: flex;
      color: #3a84ff;
      animation: rotate-loading 1s linear infinite;
    }
  }
</style>
