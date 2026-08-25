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
      class="db-collapse-table-header"
      @click="handleToggle">
      <div class="db-collapse-table-left">
        <i class="db-icon-down-shape db-collapse-table-icon" />
        <div class="db-collapse-table-title">
          <slot name="title">
            <template v-if="title">
              <strong>【{{ title }}】</strong>
              <span> - </span>
            </template>
            <I18nT
              keypath="共n个"
              tag="p">
              <strong style="color: #3a84ff">{{ nums }}</strong>
            </I18nT>
          </slot>
        </div>
      </div>
      <BkDropdown
        v-if="showIcon"
        class="db-collapse-table-dropdown"
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click"
        @click.stop>
        <i class="db-icon-more db-collapse-table-trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              v-for="(item, index) of operations"
              :key="index"
              @click="item.onClick(tableProps.data ?? [])">
              {{ item.label }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>

    <Transition mode="in-out">
      <div
        v-show="state.collapse"
        class="db-collapse-table-content">
        <PrimaryTable
          v-bind="tableProps"
          :data="renderData"
          :row-key="tableProps.rowKey ?? 'id'" />
        <div class="table-footer">
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            :model-value="pagination.current"
            @change="handlePageChange"
            @limit-change="handleLimitChange" />
        </div>
      </div>
    </Transition>
  </div>
</template>
<script lang="ts">
  import type { PrimaryTableProps } from '@components/tdesign-ui/table';

  interface Props {
    collapse?: boolean;
    operations?: CollapseTableOperation[];
    showIcon?: boolean;
    tableProps?: Partial<PrimaryTableProps>;
    title?: string;
  }

  export type CollapseTableOperation = {
    label: string;
    onClick: (params: Array<any>) => void;
  };

  export default {
    name: 'DBCollapseTable',
  };
</script>

<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    collapse: true,
    operations: () => [],
    showIcon: true,
    tableProps: () => ({}),
    title: 'Title',
  });

  const state = reactive({
    collapse: props.collapse,
  });
  const nums = computed(() => props.tableProps?.data?.length ?? 0);

  const pagination = reactive({
    align: 'right' as const,
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
  });

  const renderData = computed(() => {
    const data = props.tableProps?.data ?? [];
    const start = (pagination.current - 1) * pagination.limit;
    return data.slice(start, start + pagination.limit);
  });

  watch(
    () => props.collapse,
    () => {
      state.collapse = props.collapse;
    },
  );

  watchEffect(() => {
    pagination.count = props.tableProps?.data?.length ?? 0;
    if ((pagination.current - 1) * pagination.limit >= pagination.count) {
      pagination.current = 1;
    }
  });

  function handleToggle() {
    state.collapse = !state.collapse;
  }

  const handlePageChange = (current: number) => {
    pagination.current = current;
  };

  const handleLimitChange = (limit: number) => {
    pagination.limit = limit;
    pagination.current = 1;
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .db-collapse-table {
    font-weight: normal;
    color: @default-color;

    .db-collapse-table-header {
      height: 42px;
      padding: 0 16px;
      font-size: @font-size-mini;
      cursor: pointer;
      background-color: @bg-dark-gray;
      justify-content: space-between;
      .flex-center();
    }

    .db-collapse-table-left {
      .flex-center();
    }

    .db-collapse-table-icon {
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .db-collapse-table-title {
      .flex-center();

      padding-left: 4px;
    }

    .db-collapse-table-dropdown {
      font-size: 0;
      line-height: 20px;
    }

    .db-collapse-table-trigger {
      display: block;
      font-size: 20px;
      cursor: pointer;

      &:hover {
        background-color: @bg-disable;
        border-radius: 2px;
      }
    }

    .db-collapse-table-content {
      :deep(thead th),
      :deep(.__table-custom-setting-col__) {
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

      :deep(.domain-column) {
        .master-icon {
          display: inline-block;
          width: 20px;
          height: 20px;
          line-height: 20px;
          color: #3a84ff;
          text-align: center;
          background: #f0f5ff;
          border-radius: 2px;
        }

        .slave-icon {
          .master-icon();

          color: #1cab88;
          background: #f2fff4;
        }
      }
    }

    &.db-collapse-table--collapse {
      .db-collapse-table-icon {
        transform: rotate(0);
      }
    }
  }
</style>
