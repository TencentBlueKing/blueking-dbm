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
  <div class="aside-container">
    <BkInput
      v-model="state.search"
      class="aside-container__search"
      clearable
      :placeholder="placeholder || $t('域名')"
      type="search"
      @clear="searchClear"
      @enter="searchEnter" />
    <BkLoading
      class="aside-container__loading"
      :loading="loading">
      <div class="aside-container__list db-scroll-y">
        <template v-if="data.length !== 0">
          <div
            v-for="item of data"
            :key="item[showKey]"
            class="aside-container__item"
            :class="[
              {
                'aside-container__item--active': item[showKey] === activeItem[showKey],
              },
            ]"
            @click="handleClickItem(item)">
            <DbStatus :theme="getItemStatus(item)" />
            <span
              v-overflow-tips="{ content: item[showKey], placement: 'right' }"
              class="text-overflow">
              {{ item[showKey] }}
            </span>
          </div>
        </template>
        <EmptyStatus
          v-else
          :is-anomalies="isAnomalies"
          :is-searching="!!state.search"
          @clear-search="handleClearSearch"
          @refresh="searchEnter" />
      </div>
      <BkPagination
        v-model="state.pagination.current"
        align="center"
        class="aside-container__pagination"
        :count="state.pagination.count"
        :limit="state.pagination.limit"
        :limit-list="[limit]"
        :show-total-count="false"
        small
        @change="handleChangePage" />
    </BkLoading>
  </div>
</template>
<script lang="ts">
  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  export default {
    name: 'AsideList',
  };
</script>

<script setup lang="ts">
  interface Props {
    loading?: boolean;
    data?: { [key: string]: string }[];
    activeItem?: Record<string, any>;
    total?: number;
    limit?: number;
    showKey?: string;
    placeholder?: string;
    isAnomalies?: boolean;
  }

  interface Emits {
    (e: 'searchEnter', value: string): void;
    (e: 'searchClear', value: string): void;
    (e: 'changePage', value: number): void;
    (e: 'itemSelected', value: { [key: string]: string }): void;
    // (e: 'returnPage'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    loading: false,
    data: () => [],
    activeItem: () => ({}),
    total: 0,
    limit: 50,
    showKey: 'master_domain',
    placeholder: '',
    isAnomalies: false,
  });
  const emits = defineEmits<Emits>();

  const state = reactive({
    search: '',
    activeLocationPage: 1,
    pagination: {
      limit: 50,
      current: 1,
      count: 0,
    },
  });

  /**
   * 设置数据总数
   */
  watch(
    () => props.total,
    (value: number) => {
      state.pagination.count = value;
    },
  );

  /**
   * 设置每页数量
   */
  watch(
    () => props.limit,
    (value: number) => {
      state.pagination.limit = value;
    },
  );

  // 列表有数据 & 非搜索状态 & 列表非loading状态
  // const showReturnIcon = computed(() => props.data.length > 0 && !state.search && props.loading === false);

  /**
   * 获取状态
   */
  function getItemStatus(data: any) {
    const statusMap = {
      running: 'success',
      unavailable: 'danger',
      normal: 'success',
      abnormal: 'danger',
      restoring: 'loading',
    };
    return statusMap[data.status as keyof typeof statusMap] || 'danger';
  }

  /**
   * 搜索框 enter 事件
   */
  function searchEnter() {
    emits('searchEnter', state.search);
  }

  /**
   * 搜索框 clear 事件
   */
  function searchClear() {
    emits('searchClear', '');
  }

  function handleClearSearch() {
    state.search = '';
    searchClear();
  }

  /**
   * 返回选中页
   */
  // function handleReturnSelectedPage() {
  //   if (state.activeLocationPage === state.pagination.current) {
  //     Message({
  //       message: t('当前已经处于选中页'),
  //       theme: 'warning',
  //       delay: 1500,
  //     });
  //     return;
  //   }

  //   state.pagination.current = state.activeLocationPage;
  //   emits('returnPage', state.activeLocationPage);
  // }

  /**
   * 翻页
   */
  function handleChangePage(value: number) {
    state.pagination.current = value;
    emits('changePage', value);
  }

  /**
   * 选中列表项
   */
  function handleClickItem(data: { [key: string]: string }) {
    setActiveLocationPage(state.pagination.current);
    emits('itemSelected', data);
  }

  /**
   * 记录选中项页码
   */
  function setActiveLocationPage(value: number) {
    state.activeLocationPage = value;
  }

  /**
   * 是否需要向第一页插入数据
   */
  function isInsertToPage() {
    return state.activeLocationPage === 1 && state.pagination.current === 1;
  }

  defineExpose({
    setActiveLocationPage,
    isInsertToPage,
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .aside-container {
    position: relative;
    height: 100%;
    padding-top: 24px;

    &__loading {
      height: calc(100% - 56px);
    }

    &__search {
      display: flex;
      width: calc(100% - 40px);
      margin: 0 auto 24px;
    }

    &__list {
      height: calc(100% - 32px);
    }

    &__record {
      position: absolute;
      top: 84px;
      right: 16px;
      width: 24px;
      height: 24px;
      font-size: @font-size-mini;
      line-height: 24px;
      text-align: center;
      cursor: pointer;
      background-color: @bg-white;
      border-radius: 50%;
      box-shadow: 0 2px 3px 0 rgb(0 0 0 / 10%);

      &:hover {
        color: @primary-color;
      }
    }

    &__item {
      width: calc(100% - 1px);
      padding: 0 20px;
      font-size: @font-size-mini;
      line-height: 32px;
      cursor: pointer;
      border-top: 1px solid transparent;
      border-bottom: 1px solid transparent;

      .flex-center();

      &:hover {
        background-color: @bg-white;
      }

      &--active {
        width: 100%;
        background-color: @bg-white;
        border-top-color: @border-disable;
        border-bottom-color: @border-disable;
      }
    }

    &__pagination {
      padding: 4px 0;

      :deep(.bk-pagination-limit) {
        display: none;
      }
    }
  }
</style>
