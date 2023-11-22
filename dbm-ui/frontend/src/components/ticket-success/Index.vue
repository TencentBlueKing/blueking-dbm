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
  <div class="mysql-operation-success-page">
    <div style="font-size: 64px; color: #2dcb56;">
      <DbIcon type="check-circle-fill" />
    </div>
    <div style="margin-top: 36px; font-size: 24px; line-height: 32px; color: #313238;">
      <slot name="title" />
    </div>
    <div style="margin-top: 16px; font-size: 14px; line-height: 22px; color: #63656e;">
      <slot />
    </div>
    <div class="operation-steps">
      <div
        v-for="(item, index) in steps"
        :key="index"
        class="step-item">
        <div class="step-status">
          <div
            :class="[index === currentIndex ? 'status-loading' : 'status-dot', {
              'status-dot--success': index < currentIndex
            }]" />
        </div>
        <div>{{ item.name }}</div>
      </div>
    </div>
    <div style="margin-top: 32px;">
      <slot name="action" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';

  interface Props {
    steps: Array<{ name: string, current?: boolean }>
  }

  const props = defineProps<Props>();

  const currentIndex = computed(() => {
    const index = _.findIndex(props.steps, item => Boolean(item.current));
    return Math.max(index, 0);
  });
</script>
<style lang="less">
.mysql-operation-success-page {
  display: block;
  padding-top: 180px;
  text-align: center;

  .operation-steps {
    display: flex;
    margin-top: 24px;
    margin-bottom: 32px;
    font-size: 14px;
    line-height: 22px;
    color: #63656e;
    justify-content: center;

    .step-item {
      padding: 0 22px;

      &:first-child {
        .step-status::before {
          content: none;
        }
      }

      &:last-child {
        .step-status::after {
          content: none;
        }
      }
    }

    .step-status {
      position: relative;
      display: flex;
      height: 14px;
      margin-bottom: 20px;
      justify-content: center;
      align-items: center;

      &::before,
      &::after {
        position: absolute;
        top: 50%;
        width: calc(50% + 22px);
        height: 1px;
        background: #d8d8d8;
        content: "";
      }

      &::before {
        right: 50%;
      }

      &::after {
        left: 50%;
      }
    }

    .status-loading,
    .status-dot {
      z-index: 1;
      background: #fff;

      &--success {
        background-color: rgb(45 203 86);
        border-color: rgb(45 203 86) !important;
      }
    }

    .status-loading {
      position: relative;
      display: flex;
      width: 13px;
      height: 13px;
      border: 2px solid #3a84ff;
      border-radius: 50%;
      align-items: center;
      justify-content: center;

      &::after {
        width: 5px;
        height: 5px;
        border: 1px solid #3a84ff;
        border-top-color: white;
        border-radius: 50%;
        content: "";
        opacity: 60%;
        animation: rotate-loading 1.5s linear infinite;
      }
    }

    .status-dot {
      width: 10px;
      height: 10px;
      border: 2px solid #d8d8d8;
      border-radius: 50%;
    }
  }
}
</style>
