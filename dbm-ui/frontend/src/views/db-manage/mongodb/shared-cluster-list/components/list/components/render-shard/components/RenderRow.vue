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
      class="render-row-wrapper">
      <span ref="prefixRef">
        <slot name="prefix"></slot>
      </span>
      <span
        v-for="(item, index) in data"
        :key="index"
        class="render-row-item">
        <span v-if="index !== 0">，</span>
        {{ item }}
      </span>
    </p>
    <p class="visible-content">
      <slot name="prefix"></slot>
      <span
        v-for="(item, index) in visibleData"
        :key="index"
        class="visible-item">
        <span v-if="index !== 0">，</span>
        {{ item }}
      </span>
      <BkPopover
        v-if="overflowData.length > 0"
        placement="top">
        <BkTag
          class="ml-4"
          size="small">
          +{{ overflowData.length }}
        </BkTag>
        <template #content>
          <div
            v-for="(item, index) in overflowData"
            :key="index">
            {{ item }}
          </div>
        </template>
      </BkPopover>
    </p>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    data: string[];
  }

  const props = defineProps<Props>();

  /**
   * 获取第一个溢出文本的 index
   */
  const findOverflowIndex = () => {
    overflowIndex.value = null;

    nextTick(() => {
      if (textRef.value) {
        const { left, width } = textRef.value.getBoundingClientRect();
        const max = left + width;
        const htmlArr: Element[] = Array.from(textRef.value.getElementsByClassName('render-row-item'));

        for (let i = 0; i < htmlArr.length; i++) {
          const item = htmlArr[i];
          const { left: itemLeft, width: itemWidth } = item.getBoundingClientRect();
          if (itemLeft + itemWidth > max) {
            overflowIndex.value = i;
            break;
          }
        }
      }
    });
  };

  const rowRef = ref<HTMLDivElement>();
  useResizeObserver(rowRef, debounce(findOverflowIndex, 200));

  const textRef = ref<HTMLParagraphElement>();
  const prefixRef = ref<HTMLParagraphElement>();
  const overflowIndex = ref<number | null>(null);

  const overflowData = computed(() => {
    if (overflowIndex.value === null) {
      return [];
    }
    return props.data.slice(overflowIndex.value);
  });

  const visibleData = computed(() => {
    if (overflowIndex.value === null) {
      return props.data;
    }
    return props.data.slice(0, overflowIndex.value);
  });

  watch(() => props.data, findOverflowIndex, { immediate: true });
</script>

<style lang="less" scoped>
  .render-row {
    position: relative;
    display: flex;
    max-width: 100%;
    align-items: center;

    .render-row-wrapper {
      display: flex;
      overflow: hidden;
      opacity: 0%;
    }

    .visible-content {
      position: absolute;
      display: flex;
      align-items: center;
    }
  }
</style>
