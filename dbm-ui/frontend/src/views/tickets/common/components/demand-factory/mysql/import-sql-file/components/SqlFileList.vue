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
  <div class="sql-execute-sql-file-list">
    <div class="file-list-title">
      <span>{{ $t('文件列表') }}</span>
      <span style="font-size: 12px; font-weight: normal; color: #979ba5">
        {{ $t('按顺序执行') }}
      </span>
    </div>
    <div class="file-list">
      <div
        v-for="fileItemData in localList"
        :key="fileItemData.name"
        class="file-item"
        :class="{
          active: fileItemData.name === modelValue,
        }"
        @click="handleClick(fileItemData.name)">
        <span v-overflow-tips>{{ getSQLFilename(fileItemData.name) }}</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';

  import { getSQLFilename } from '@utils';

  interface Props {
    modelValue: string;
    data: Array<string>;
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const localList = ref<Array<Record<'id' | 'name', string>>>([]);

  watch(
    () => props.data,
    () => {
      localList.value = props.data.map((fileName) => ({
        id: fileName,
        name: fileName,
      }));
      const fileName = localList.value[0].name;
      emits('update:modelValue', fileName);
    },
    {
      immediate: true,
    },
  );

  const handleClick = (fileName: string) => {
    emits('update:modelValue', fileName);
  };
</script>
<style lang="less">
  @keyframes rotate-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .sql-execute-sql-file-list {
    width: 238px;
    height: 500px;
    padding-top: 18px;
    border-right: 1px solid #3d3d40;

    .file-list-title {
      padding: 0 16px;
      font-weight: bold;
      line-height: 16px;
      color: #fff;
    }

    .file-list {
      display: flex;
      padding: 22px 12px;
      font-size: 12px;
      color: #c4c6cc;
      flex-direction: column;

      .file-item {
        display: flex;
        align-items: center;
        height: 36px;
        padding: 0 8px;
        cursor: pointer;
        background: rgb(255 255 255 / 8%);
        border-radius: 2px;

        &:hover {
          background: rgb(255 255 255 / 20%);
        }

        &.active {
          font-weight: bold;
          color: #fff;
          background: #1768ef;
          opacity: 100% !important;
        }

        &.is-error {
          color: rgb(255 86 86 / 100%);
          background: rgb(255 86 86 / 21%);
        }

        & ~ .file-item {
          margin-top: 8px;
        }
      }
    }
  }
</style>
