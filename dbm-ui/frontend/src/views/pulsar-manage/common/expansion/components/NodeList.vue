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
  <div class="node-list">
    <div
      v-for="nodeItem in nodeList"
      :key="nodeItem"
      class="node-item"
      :class="{ active: modelValue === nodeItem }"
      @click="handleSelect(nodeItem)">
      <div>{{ getDisplayName(nodeItem) }}</div>
      <div
        v-bk-tooltips="calcStatus(nodeInfo[nodeItem]).tips"
        style="margin-left: auto;">
        <DbIcon v-bind="calcStatus(nodeInfo[nodeItem])" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { TNodeInfo } from '../Index.vue';

  interface Props {
    modelValue: string,
    nodeInfo: Record<string, TNodeInfo>
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const getDisplayName = (name = '') => name.slice(0, 1).toUpperCase() + name.slice(1);

  const calcStatus = (nodeInfo: TNodeInfo) => {
    if (!nodeInfo.targetDisk || !nodeInfo.hostList) {
      return {};
    }

    // 配置不完整
    if (nodeInfo.hostList.length < 1) {
      return {
        type: 'exclamation-fill',
        style: {
          color: '#ea3636',
        },
        tips: t('配置不完整'),
      };
    }

    // 容量不匹配
    const {
      totalDisk,
      targetDisk,
      expansionDisk,
    } = nodeInfo;
    const realTargetDisk = totalDisk + expansionDisk;

    if (realTargetDisk - targetDisk > 1 || realTargetDisk - targetDisk < -1) {
      return {
        type: 'exclamation-fill',
        style: {
          color: '#ff9c01',
        },
        tips: t('与目标容量不匹配'),
      };
    }
    // 配置正确
    return {
      type: 'check-circle-fill',
      style: {
        color: '#2dcb56',
      },
      tips: t('匹配目标容量'),
    };
  };

  const nodeList = [
    'bookkeeper',
    'broker',
  ];

  const handleSelect = (value: string) => {
    emits('update:modelValue', value);
  };
</script>
<style lang="less" scoped>
  .node-list {
    width: 160px;
    padding: 12px;
    background: #fff;
    border-right: 1px solid #f0f1f5;

    .node-item {
      display: flex;
      height: 32px;
      padding: 0 8px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      background: #f5f7fa;
      align-items: center;
      transition: 0.1s;

      &:hover {
        background: #f0f5ff;
      }

      &.active {
        color: #3a84ff;
        background: #f0f5ff;
      }

      & ~ .node-item {
        margin-top: 3px;
      }
    }
  }
</style>
