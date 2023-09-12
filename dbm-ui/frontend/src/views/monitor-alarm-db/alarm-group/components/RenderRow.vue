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
      <span
        v-for="(item, index) in data"
        :key="index"
        class="render-row-span">
        <BkTag class="render-row-item">
          <template #icon>
            <DbIcon
              class="render-row-icon"
              :type="item.type" />
          </template>
          {{ item.id }}
        </BkTag>
      </span>
    </p>
    <BkPopover
      allow-html
      content="#hidden-pop-content"
      placement="top"
      render-type="auto"
      theme="light"
      width="400px">
      <BkTag v-if="overflowData.length > 0">
        +{{ overflowData.length }}
      </BkTag>
    </BkPopover>
    <div
      class="render-row"
      style="display: none;">
      <div id="hidden-pop-content">
        <BkTag
          v-for="item in overflowData"
          :key="item.type"
          class="render-row-item">
          <template #icon>
            <DbIcon
              class="render-row-icon"
              :type="item.type" />
          </template>
          {{ item.id }}
        </BkTag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    data: {
      type: string,
      id: string
    }[]
  }

  const props = defineProps<Props>();

  const rowRef = ref<HTMLDivElement>();
  const textRef = ref<HTMLParagraphElement>();
  const overflowIndex = ref<number | null>(null);
  const overflowData = computed(() => {
    if (overflowIndex.value === null) return [];

    return props.data.slice(overflowIndex.value);
  });

  /**
   * 获取第一个溢出文本的 index
   */
  const findOverflowIndex = () => {
    overflowIndex.value = null;

    nextTick(() => {
      if (textRef.value) {
        const { left, width } = textRef.value.getBoundingClientRect();
        const max = left + width;
        const htmlArr: Element[] = Array.from(textRef.value.getElementsByClassName('render-row-span'));

        for (let i = 0; i < htmlArr.length; i++) {
          const item = htmlArr[i];
          const { left: spanLeft, width: spanWidth } = item.getBoundingClientRect();

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

    .render-row-wrapper {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }

    .render-row-item {
      padding: 0 10px 0 4px;
    }

    .render-row-icon {
      font-size: 20px;
    }
  }
</style>
