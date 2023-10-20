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
      <BkTag
        v-for="item in data"
        :key="item.id"
        class="render-row-item">
        <template #icon>
          <DbIcon
            class="render-row-icon"
            :type="getIconType(item.type)" />
        </template>
        {{ item.displayName }}
      </BkTag>
      <BkTag class="overflow-collapse-tag">
        +{{ overflowData.length }}
      </BkTag>
    </p>
    <p class="visible-content">
      <BkTag
        v-for="item in visibleData"
        :key="item.id"
        class="render-row-item">
        <template #icon>
          <DbIcon
            class="render-row-icon"
            :type="getIconType(item.type)" />
        </template>
        {{ item.displayName }}
      </BkTag>
      <BkPopover
        placement="top"
        render-type="auto"
        theme="light"
        width="400px">
        <BkTag
          v-if="overflowData.length > 0"
          class="overflow-collapse-tag">
          +{{ overflowData.length }}
        </BkTag>
        <template #content>
          <BkTag
            v-for="item in overflowData"
            :key="item.id"
            class="render-row-item">
            <template #icon>
              <DbIcon
                class="render-row-icon"
                :type="getIconType(item.type)" />
            </template>
            {{ item.displayName }}
          </BkTag>
        </template>
      </BkPopover>
    </p>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    data: {
      id: string,
      displayName: string,
      type: string
    }[]
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
        const colTag = textRef.value.getElementsByClassName('overflow-collapse-tag');
        if (colTag.length) {
          const { left: colTagLeft, width: colTagWidth } = colTag[0].getBoundingClientRect();
          if (colTagLeft + colTagWidth > max && overflowIndex.value) {
            overflowIndex.value = overflowIndex.value - 1;
          }
        }
      }
    });
  };

  const rowRef = ref<HTMLDivElement>();
  useResizeObserver(rowRef, debounce(findOverflowIndex, 300));

  const textRef = ref<HTMLParagraphElement>();
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

  const getIconType = (type: string) => (type === 'group' ? 'yonghuzu' : 'dba-config');
</script>

<style lang="less" scoped>
  .render-row {
    position: relative;
    display: inline-flex;
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
    }
  }

  .render-row-item {
    padding: 0 10px 0 4px;
  }

  .render-row-icon {
    font-size: 17.5px;
  }
</style>
