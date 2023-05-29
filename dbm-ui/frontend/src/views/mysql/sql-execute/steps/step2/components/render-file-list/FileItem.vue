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
    class="render-file-item"
    :class="{
      active: data.name === active,
      'is-failed': data.isFailed,
    }"
    @click="handleClick">
    <div class="file-name">
      {{ data.name }}
    </div>
    <div class="status-box">
      <div
        v-if="data.isPending"
        class="rotate-loading">
        <DbIcon
          svg
          type="sync-pending" />
      </div>
      <DbIcon
        v-else-if="data.isFailed"
        style="color: #ea3636"
        type="delete-fill" />
      <DbIcon
        v-else-if="data.isSuccessed"
        style="color: #2dcb56"
        type="check-circle-fill" />
      <span
        v-else
        style="font-size: 12px; color: #63656e">
        {{ $t('待执行') }}
      </span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { IFileItem } from './Index.vue';

  interface Props {
    data: IFileItem;
    active: string;
  }

  interface Emits {
    (e: 'click'): void;
  }

  defineProps<Props>();
  const emtis = defineEmits<Emits>();

  const handleClick = () => {
    emtis('click');
  };
</script>
<style lang="less">
  .render-file-item {
    display: flex;
    height: 36px;
    padding: 0 12px;
    color: #c4c6cc;
    cursor: pointer;
    background: rgb(255 255 255 / 8%);
    border-radius: 2px;
    align-items: center;

    & ~ .render-file-item {
      margin-top: 8px;
    }

    &.is-failed {
      color: #ff5656;
      background: rgb(255 86 86 / 8%);
    }

    &.active {
      font-weight: 700;
      color: #fff;
      background: #1768ef;
    }

    .file-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .status-box {
      display: flex;
      height: 14px;
      padding-left: 4px;
      margin-left: auto;
      font-size: 14px;
      word-break: keep-all;
      user-select: none;
      align-items: center;

      .rotate-loading {
        display: flex;
      }
    }
  }
</style>
