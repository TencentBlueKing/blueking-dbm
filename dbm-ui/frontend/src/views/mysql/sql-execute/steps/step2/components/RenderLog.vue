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
    ref="rootRef"
    class="execute-sql-render-log"
    @scroll="handleScroll">
    <div
      v-for="(item, index) in data"
      :key="index"
      class="log-line">
      <div class="line-number">
        {{ index + 1 }}
      </div>
      <!-- eslint-disable vue/no-v-html -->
      <div
        class="line-content"
        v-html="parse(item.message)" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    onMounted,
    ref,
    watch,
  } from 'vue';

  import { escapeHTML } from '@utils';

  interface Props {
    data: any[]
  }

  const props = defineProps<Props>();

  const parseReg = /^##\[([^\]]+)\](.*)$/;
  const rootRef = ref();

  const colorMap = {
    command: 'rgba(146,166,202,1)',
    info: 'rgba(127,202,84,1)',
    warning: 'rgba(246,222,84,1)',
    error: 'rgba(247,49,49,1)',
    debug: 'rgba(99,176,106,1)',
  };
  let willAutoScroll = true;

  watch(() => props.data, (newData, originalData) => {
    if (newData.length === originalData.length) {
      return;
    }
    if (willAutoScroll) {
      setTimeout(() => {
        rootRef.value.scrollTop = rootRef.value.scrollHeight;
      });
    }
  });

  const parse = (text: string) => {
    const levelMatch = text.match(parseReg);
    if (levelMatch) {
      const [
        level,
        message,
      ] = levelMatch.slice(1) as [keyof typeof colorMap, string];

      const renderMessage = escapeHTML(message);
      if (!colorMap[level]) {
        return renderMessage;
      }
      return `<span style="color: ${colorMap[level]}">${renderMessage}</span>`;
    }
    return text;
  };

  const handleScroll = () => {
    willAutoScroll = rootRef.value.scrollHeight - rootRef.value.scrollTop
      < rootRef.value.getBoundingClientRect().height + 30;
  };

  onMounted(() => {
    const lineNumberList = rootRef.value.querySelectorAll('.line-number') as HTMLElement[];

    let maxLineNumberWidth = 0;
    _.forEachRight(Array.from(lineNumberList), (itemEl: HTMLElement) => {
      const { width } = itemEl.getBoundingClientRect();
      maxLineNumberWidth = Math.max(maxLineNumberWidth, width);
      // eslint-disable-next-line no-param-reassign
      itemEl.style.width = `${maxLineNumberWidth}px`;
    });
  });
</script>
<style lang="less">
  .execute-sql-render-log {
    display: block;
    height: 100%;
    padding: 12px 0;
    overflow: auto;
    font-size: 12px;
    line-height: 22px;
    color: #b0b2b8;
    background: #1a1a1a;

    .log-line {
      display: flex;

      .line-number {
        padding-right: 16px;
        padding-left: 8px;
        font-size: 13px;
        color: #63656e;
        text-align: right;
        white-space: nowrap;
        user-select: none;
      }

      .line-content {
        flex: 1;

        &:hover {
          color: #fff;
          background: rgb(51 48 48);
        }
      }
    }
  }
</style>
