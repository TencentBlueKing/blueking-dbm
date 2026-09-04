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
    class="ip-selector-collapse-table"
    :class="{ 'ip-selector-collapse-table-expand': collapse }">
    <div
      class="ip-selector-collapse-table-header"
      @click="handleToggle">
      <div class="ip-selector-collapse-table-left">
        <i class="db-icon-down-shape ip-selector-collapse-table-icon" />
        <div class="ip-selector-collapse-table-title">
          <slot name="title">
            <strong>【{{ title }}】</strong>
            <span> - </span>
            <I18nT
              keypath="共n个"
              tag="p">
              <strong style="color: #3a84ff">{{ data.length }}</strong>
            </I18nT>
          </slot>
        </div>
      </div>
      <BkDropdown
        class="ip-selector-collapse-table-dropdown"
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click"
        @click.stop>
        <i class="db-icon-more ip-selector-collapse-table-trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              v-for="(item, index) of operations"
              :key="index"
              @click="item.onClick()">
              {{ item.label }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <Transition mode="in-out">
      <div
        v-show="collapse"
        class="ip-selector-collapse-table-content">
        <PrimaryTable
          :bk-ui-settings="bkUiSettings"
          :data="renderData"
          :max-height="474"
          row-key="id">
          <slot />
        </PrimaryTable>
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          :model-value="pagination.current"
          @change="handlePageChange"
          @limit-change="handleLimitChange" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
  import type { BkUiSettings, TableRowData } from '@components/tdesign-ui/table';

  interface Props {
    bkUiSettings?: BkUiSettings;
    data: TableRowData[];
    operations: {
      label: string;
      onClick: () => void;
    }[];
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    bkUiSettings: undefined,
    title: '',
  });

  const collapse = ref(true);

  const pagination = reactive({
    align: 'right' as const,
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
  });

  const renderData = computed(() => {
    const start = (pagination.current - 1) * pagination.limit;
    return props.data.slice(start, start + pagination.limit);
  });

  watchEffect(() => {
    pagination.count = props.data.length;
    if ((pagination.current - 1) * pagination.limit >= pagination.count) {
      pagination.current = 1;
    }
  });

  const handleToggle = () => {
    collapse.value = !collapse.value;
  };

  const handlePageChange = (current: number) => {
    pagination.current = current;
  };

  const handleLimitChange = (limit: number) => {
    pagination.limit = limit;
    pagination.current = 1;
  };
</script>

<style lang="less" scoped>
  .ip-selector-collapse-table {
    font-weight: normal;
    color: @default-color;

    .ip-selector-collapse-table-header {
      display: flex;
      align-items: center;
      height: 42px;
      padding: 0 16px;
      font-size: @font-size-mini;
      cursor: pointer;
      background-color: @bg-dark-gray;
      justify-content: space-between;
    }

    .ip-selector-collapse-table-left {
      display: flex;
      align-items: center;
    }

    .ip-selector-collapse-table-icon {
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .ip-selector-collapse-table-title {
      display: flex;
      align-items: center;
      padding-left: 4px;
    }

    .ip-selector-collapse-table-dropdown {
      font-size: 0;
      line-height: 20px;
    }

    .ip-selector-collapse-table-trigger {
      display: block;
      font-size: 20px;
      cursor: pointer;

      &:hover {
        background-color: @bg-disable;
        border-radius: 2px;
      }
    }

    .ip-selector-collapse-table-content {
      :deep(thead th) {
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

    &.ip-selector-collapse-table-expand {
      .ip-selector-collapse-table-icon {
        transform: rotate(0);
      }
    }
  }
</style>
