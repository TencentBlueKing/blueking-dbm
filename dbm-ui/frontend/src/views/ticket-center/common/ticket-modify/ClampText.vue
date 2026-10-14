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
  <div class="ticket-modify-clamp-text">
    <div
      ref="content"
      v-bk-tooltips="{
        content: text,
        disabled: expandable || !isOverflow,
        extCls: 'ticket-modify-clamp-text-tips',
      }"
      class="ticket-modify-clamp-text-content"
      :style="isExpanded || !lines ? {} : { '-webkit-line-clamp': lines }">
      {{ text }}
    </div>
    <BkButton
      v-if="expandable && (isOverflow || isExpanded)"
      text
      theme="primary"
      @click="handleToggle">
      {{ isExpanded ? t('收起') : t('展开') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    // true：超出时给「展开 / 收起」；false：超出时悬浮展示全文
    expandable?: boolean;
    // 最多展示行数，0 为不折叠
    lines?: number;
    text: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    expandable: false,
    lines: 2,
  });

  const { t } = useI18n();

  const contentRef = useTemplateRef<HTMLElement>('content');

  const isExpanded = ref(false);
  const isOverflow = ref(false);

  const checkOverflow = () => {
    if (!contentRef.value) {
      return;
    }
    isOverflow.value = contentRef.value.scrollHeight > contentRef.value.clientHeight + 1;
  };

  watch(
    () => [props.text, props.lines],
    () => {
      isExpanded.value = false;
      nextTick(checkOverflow);
    },
    {
      immediate: true,
    },
  );

  const handleToggle = () => {
    isExpanded.value = !isExpanded.value;
  };
</script>
<style lang="less">
  .ticket-modify-clamp-text {
    .ticket-modify-clamp-text-content {
      display: -webkit-box;
      overflow: hidden;
      word-break: break-all;
      white-space: pre-wrap;
      -webkit-box-orient: vertical;
    }
  }

  .ticket-modify-clamp-text-tips {
    max-width: 480px;
    word-break: break-all;
    white-space: pre-wrap;
  }
</style>
