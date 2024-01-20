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
  <div
    ref="rowRef"
    class="render-row">
    <p
      ref="textRef"
      class="text-overflow">
      <span
        v-for="(text,index) in data"
        :key="index">
        {{ text }} {{ index < data.length - 1 ? ' , ' : '' }}
      </span>
    </p>
    <BkTag
      v-if="overflowData.length > 0"
      v-bk-tooltips="tipList"
      class="render-row-tag">
      {{ sign }}
      {{ count }}
    </BkTag>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    data: string[],
    showAll?: boolean,
  }

  const props = defineProps<Props>();

  const rowRef = ref<HTMLDivElement>();
  const textRef = ref<HTMLParagraphElement>();
  const overflowIndex = ref<number | null>(null);

  const sign = computed(() => `${props.showAll ? '' : '+'}`);
  const overflowData = computed(() => {
    if (overflowIndex.value === null) return [];

    return props.data.slice(overflowIndex.value);
  });
  const count = computed(() => (props.showAll ? props.data.length : overflowData.value.length));
  const tipList = computed(() => (props.showAll ? props.data.join('\n') : overflowData.value.join('\n')));

  /**
   * 获取第一个溢出文本的 index
   */
  const findOverflowIndex = () => {
    overflowIndex.value = null;

    nextTick(() => {
      if (textRef.value) {
        const { left, width } = textRef.value.getBoundingClientRect();
        const max = left + width;
        const spans: HTMLSpanElement[] = Array.from(textRef.value.getElementsByTagName('span'));
        for (let i = 0;i < spans.length; i++) {
          const span = spans[i];
          const { left: spanLeft, width: spanWidth } = span.getBoundingClientRect();

          if (spanLeft + spanWidth > max) {
            overflowIndex.value = i;
            break;
          }
        }
      }
    });
  };

  watch(() => props.data, findOverflowIndex, { immediate: true });
  useResizeObserver(rowRef, debounce(findOverflowIndex, 300));
</script>

<style lang="less" scoped>
  .render-row {
    display: inline-flex;
    max-width: 100%;
    align-items: center;

    &-tag {
      flex-shrink: 0;
      margin: 0 4px;
    }
  }
</style>
