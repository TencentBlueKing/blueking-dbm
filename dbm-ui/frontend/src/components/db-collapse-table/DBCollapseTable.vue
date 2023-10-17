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
    class="db-collapse-table"
    :class="[{ 'db-collapse-table--collapse': state.collapse }]">
    <div
      class="db-collapse-table__header"
      @click="handleToggle">
      <div class="db-collapse-table__left">
        <i class="db-icon-down-shape db-collapse-table__icon" />
        <div class="db-collapse-table__title">
          <slot name="title">
            <template v-if="title">
              <strong>【{{ title }}】</strong>
              <span> - </span>
            </template>
            <I18nT
              keypath="共n个"
              tag="p">
              <strong style="color: #3a84ff;">{{ nums }}</strong>
            </I18nT>
          </slot>
        </div>
      </div>
      <BkDropdown
        v-if="showIcon"
        class="db-collapse-table__dropdown"
        @click.stop>
        <i class="db-icon-more db-collapse-table__trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              v-for="(item, index) of operations"
              :key="index"
              @click="item.onClick(tableProps.data)">
              {{ item.label }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>

    <Transition mode="in-out">
      <DbOriginalTable
        v-show="state.collapse"
        class="db-collapse-table__content"
        v-bind="tableProps" />
    </Transition>
  </div>
</template>
<script lang="ts">
  import type { TablePropTypes } from 'bkui-vue/lib/table/props';

  export type CollapseTableOperation = {
    label: string,
    onClick: (params: Array<any>) => void
  };

  export type ClusterTableProps = {
    -readonly [K in keyof TablePropTypes]: TablePropTypes[K]
  }

  export default {
    name: 'DBCollapseTable',
  };
</script>

<script setup lang="ts">
  interface Props {
    collapse?: boolean,
    title?: string,
    tableProps?: {
      data: TablePropTypes['data'],
      columns: TablePropTypes['columns'],
    },
    operations?: CollapseTableOperation[],
    showIcon?: boolean,
  }

  const props = withDefaults(defineProps<Props>(), {
    collapse: true,
    title: 'Title',
    tableProps: () => ({
      data: [] as TablePropTypes['data'],
      columns: [] as TablePropTypes['columns'],
    }),
    operations: () => ([]),
    showIcon: true,
  });

  const state = reactive({
    collapse: props.collapse,
  });
  const nums = computed(() => props.tableProps?.data?.length ?? 0);

  watch(() => props.collapse, () => {
    state.collapse = props.collapse;
  });

  function handleToggle() {
    state.collapse = !state.collapse;
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .db-collapse-table {
    font-weight: normal;
    color: @default-color;

    &__header {
      height: 42px;
      padding: 0 16px;
      font-size: @font-size-mini;
      cursor: pointer;
      background-color: @bg-dark-gray;
      justify-content: space-between;
      .flex-center();
    }

    &__left {
      .flex-center();
    }

    &__icon {
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    &__title {
      .flex-center();

      padding-left: 4px;
    }

    &__dropdown {
      font-size: 0;
      line-height: 20px;
    }

    &__trigger {
      display: block;
      font-size: 20px;
      cursor: pointer;

      &:hover {
        background-color: @bg-disable;
        border-radius: 2px;
      }
    }

    &__content {
      :deep(thead th),
      :deep(.table-head-settings) {
        background-color: #f5f7fa !important;
      }

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }

      :deep(.bk-pagination-limit-select) {
        .bk-input {
          border-color: #f0f1f5;
        }
      }
    }

    &--collapse {
      .db-collapse-table__icon {
        transform: rotate(0);
      }
    }
  }
</style>
