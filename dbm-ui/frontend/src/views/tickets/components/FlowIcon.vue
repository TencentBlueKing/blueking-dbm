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
  <div class="flow-icon">
    <template v-if="data.flow_type === 'TIMER'">
      <DbIcon
        class="timer-icon"
        :class="{
          'timer-icon--success': successColors.includes(status),
          'timer-icon--fail': errorColors.includes(status),
        }"
        type="timed-task" />
    </template>
    <span
      v-else-if="status === 'RUNNING'"
      class="flow-icon--loading" />
    <span
      v-else-if="successColors.includes(status)"
      class="flow-icon-dot--success flow-icon-dot" />
    <span
      v-else-if="errorColors.includes(status)"
      class="flow-icon-dot--fail flow-icon-dot" />
    <span
      v-else
      class="flow-icon-dot" />
  </div>
</template>

<script setup lang="ts">
  import type { FlowItem } from '@services/types/ticket';

  interface Props {
    data: FlowItem
  }

  const props = defineProps<Props>();

  const errorColors = ['FAILED', 'REVOKED'];
  const successColors = ['SKIPPED', 'SUCCEEDED'];
  const status = computed(() => props.data.status);
</script>

<style lang="less" scoped>
.flow-icon {
  display: flex;
  flex-direction: column;
  align-items: center;

  &--loading {
    position: relative;
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #d8d8d8;
    border-color: @border-primary;
    border-radius: 50%;

    &::after {
      position: absolute;
      top: 1px;
      left: 1px;
      width: 6px;
      height: 6px;
      border: 1px solid @border-primary;
      border-top-color: white;
      border-radius: 50%;
      content: "";
      animation: flow-success-spin 1.5s linear infinite;
    }
  }

  .flow-icon-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    background-color: #fff;
    border: 2px solid #d8d8d8;
    border-radius: 50%;

    &--success {
      background-color: #2dcb56;
      border-color: #2dcb56;
    }

    &--fail {
      background-color: #ea3636;
      border-color: #ea3636;
    }
  }

  .timer-icon {
    font-size: 14px;
    color: #d8d8d8;

    &--success {
      color: #2dcb56;
    }

    &--fail {
      color: #ea3636;
    }
  }
}

@keyframes flow-success-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
