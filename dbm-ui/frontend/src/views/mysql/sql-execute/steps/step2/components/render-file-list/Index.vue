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
  <div class="file-list">
    <div class="header">
      <span>{{ $t('文件列表') }}</span>
      <span style="font-weight: normal; color: #979ba5;">{{ $t('按顺序执行') }}</span>
    </div>
    <div class="file-wrapper">
      <FileItem
        v-for="(item, index) in list"
        :key="`${item}_${index}`"
        :active="modelValue"
        :data="item"
        @click="handleClick(item)" />
    </div>
  </div>
</template>
<script lang="ts">
  export interface IFileItem {
    name: string,
    isPending: boolean,
    isSuccessed: boolean,
    isFailed: boolean,
    isWaiting: boolean,
  }
</script>
<script setup lang="ts">
  import FileItem from './FileItem.vue';


  interface Props {
    list: Array<IFileItem>,
    modelValue: string,
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const handleClick = (fileData: IFileItem) => {
    emits('update:modelValue', fileData.name);
  };
</script>
<style lang="less" scoped>
  .file-list {
    height: 100%;
    padding: 18px 12px;
    font-size: 12px;
    color: #c4c6cc;
    background: #2e2e2e;
    box-shadow: 1px 0 0 0 #3d3d40;

    .header {
      font-size: 12px;
      font-weight: bold;
      line-height: 16px;
      color: #fff;
    }

    .file-wrapper {
      margin-top: 22px;

      .file-item {
        display: flex;
        height: 36px;
        padding: 0 12px;
        color: #c4c6cc;
        cursor: pointer;
        background: rgb(255 255 255 / 8%);
        border-radius: 2px;
        align-items: center;

        & ~ .file-item {
          margin-top: 8px;
        }

        &.active {
          font-weight: 700;
          color: #fff;
          background: #1768ef;
        }
      }
    }
  }
</style>
