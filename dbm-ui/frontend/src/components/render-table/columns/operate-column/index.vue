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
  <FixedColumn>
    <div class="action-box">
      <div
        v-if="showAdd"
        class="action-btn"
        @click="handleAppend">
        <DbIcon type="plus-fill" />
      </div>
      <div
        v-if="showRemove"
        class="action-btn"
        :class="{
          disabled: removeable,
        }"
        @click="handleRemove">
        <DbIcon type="minus-fill" />
      </div>
    </div>
  </FixedColumn>
</template>
<script setup lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';

  interface Props {
    showAdd?: boolean;
    showRemove?: boolean;
    removeable?: boolean;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'remove'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    showAdd: true,
    showRemove: true,
    removeable: true,
  });

  const emits = defineEmits<Emits>();

  const handleAppend = () => {
    emits('add');
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };
</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    height: 42px;
    padding: 0 16px;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
