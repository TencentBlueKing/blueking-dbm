<!--
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
-->

<template>
  <div
    ref="root"
    class="global-timeout-summary">
    <div
      v-if="items.length"
      class="timeout-summary-items"
      :class="{ 'is-narrow': isNarrow }">
      <TextOverflowLayout
        v-for="item in items.slice(0, visibleCount)"
        :key="item.key">
        {{ item.text }}
      </TextOverflowLayout>
    </div>
    <span v-else>--</span>
    <BkPopover
      v-if="items.length > visibleCount"
      :arrow="false"
      ext-cls="global-timeout-summary-overlay"
      placement="bottom-start"
      theme="light"
      trigger="click">
      <BkButton
        text
        theme="primary">
        {{ t('查看全部') }}
      </BkButton>
      <template #content>
        <div class="timeout-summary-popover">
          <div class="timeout-summary-title">{{ data.ticket_type_display }} · {{ t('超时自动终止') }}</div>
          <div
            v-for="item in items"
            :key="item.key"
            class="timeout-summary-detail">
            <span class="timeout-summary-label">{{ item.label }}</span>
            <span class="timeout-summary-value">{{ item.value }}</span>
          </div>
        </div>
      </template>
    </BkPopover>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    data: TicketFlowDescribeModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const root = ref<HTMLElement>();
  const isNarrow = ref(true);
  const visibleCount = computed(() => isNarrow.value ? 2 : 4);
  const items = computed(() => props.data.effectiveExpireTypes.map((state) => {
    const hours = props.data.configs.expire_config?.[state.value] ?? -1;
    const value = hours === -1 ? t('永不') : t('n 小时', { n: hours });
    return {
      key: state.value,
      label: state.label,
      text: `${state.label}：${value}`,
      value,
    };
  }));

  useResizeObserver(root, ([entry]) => {
    isNarrow.value = entry.contentRect.width < 320;
  });
</script>

<style lang="less" scoped>
  .global-timeout-summary {
    width: 100%;
    padding: 4px 0;
    font-size: 12px;
    line-height: 20px;

    .timeout-summary-items {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 4px 8px;

      &.is-narrow {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  }

  :global(.global-timeout-summary-overlay.bk-popover) {
    box-sizing: border-box;
    width: 320px;
    max-height: 360px;
    padding: 14px 16px;
    overflow-y: auto;
    border: 1px solid #dcdee5;
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, .16);
  }

  .timeout-summary-popover {
    font-size: 12px;

    .timeout-summary-title {
      margin-bottom: 12px;
      font-size: 14px;
      font-weight: 500;
      color: #313238;
    }

    .timeout-summary-detail {
      display: flex;
      padding: 4px 0;
      line-height: 1.5;
      color: #63656e;
      gap: 16px;
    }

    .timeout-summary-label {
      flex-shrink: 0;
      width: 64px;
      word-break: break-word;
    }

    .timeout-summary-value {
      flex-shrink: 0;
      color: #313238;
    }
  }
</style>
