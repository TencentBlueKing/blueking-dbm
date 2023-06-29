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
  <div class="cluster-expansion-node-status-box">
    <div
      v-for="nodeItem in list"
      :key="nodeItem.key"
      class="node-item"
      :class="{ active: modelValue === nodeItem.key }"
      @click="handleSelect(nodeItem.key)">
      <div class="node-item-name">
        {{ nodeItem.label }}
      </div>
      <template v-if="validateStatusMemo[nodeItem.key]">
        <div
          v-if="nodeInfo[nodeItem.key].expansionDisk"
          class="disk-tips">
          <span class="number">{{ nodeInfo[nodeItem.key].expansionDisk }}</span>
          <span>G</span>
        </div>
        <div
          v-else
          class="empty-tips">
          <span>{{ t('未填写') }}</span>
        </div>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { TExpansionNode } from './Index.vue';

  interface Props {
    list: Array<{
      key: string,
      label: string
    }>,
    nodeInfo: Record<string, TExpansionNode>,
    ipSource: string
  }
  interface Exposes {
    validate: () => boolean
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const validateStatusMemo = reactive(props.list.reduce((result, item) => ({
    ...result,
    [item.key]: false,
  }), {} as Record<string, boolean>));

  const handleSelect = (value: string) => {
    validateStatusMemo[modelValue.value] = true;
    modelValue.value = value;
  };

  defineExpose<Exposes>({
    validate() {
      Object.keys(validateStatusMemo).forEach(key => validateStatusMemo[key] = true);
      return Object.values(props.nodeInfo).some((nodeData) => {
        if (props.ipSource === 'manual_input') {
          return nodeData.hostList.length > 0;
        }
        return nodeData.resourceSpec.spec_id > 0 && nodeData.resourceSpec.count > 0;
      });
    },
  });
</script>
<style lang="less">
  .cluster-expansion-node-status-box {
    width: 185px;
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
        font-weight: bold;
        color: #3a84ff;
        background: #f0f5ff;
      }

      & ~ .node-item {
        margin-top: 4px;
      }

      .node-item-name{
        padding-right: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 0 1 auto;
      }
    }

    .empty-tips{
      margin-left: auto;
      font-weight: normal;
      color: #C4C6CC;
      flex: 0 0 auto;
    }

    .disk-tips{
      margin-left: auto;
      font-weight: normal;
      color: #63656E;
      flex: 0 0 auto;
    }
  }
</style>
