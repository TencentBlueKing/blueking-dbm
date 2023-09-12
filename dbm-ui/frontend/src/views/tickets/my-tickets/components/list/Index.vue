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
  <div class="ticket-side">
    <div class="ticket-side__top">
      <div class="ticket-side__header">
        <strong>{{ $t('申请列表') }}</strong>
        <BkDropdown
          :is-show="isShowDropdown"
          trigger="click"
          @hide="handleClose">
          <div
            class="status-trigger"
            :class="{ 'is-active': isShowDropdown }"
            @click="handleToggle">
            <span>{{ activeItemInfo?.label }}</span>
            <DbIcon type="down-big status-trigger-icon" />
          </div>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem
                v-for="item in filters"
                :key="item.value"
                :class="{'dropdown-item-active': item.value === state.filters.status}"
                @click="handleChangeStatus(item)">
                {{ item.label }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
      <ListTabs @change="handleChangeTab" />
      <DbSearchSelect
        v-model="state.filters.search"
        :data="searchSelectData"
        :placeholder="$t('单号_单据类型_业务')"
        unique-select
        @change="handleChangePage(1)" />
    </div>
    <div class="ticket-side__main">
      <div
        ref="sideListRef"
        class="ticket-side__list db-scroll-y">
        <BkLoading :loading="state.isLoading">
          <EmptyStatus
            v-if="state.list.length === 0"
            :is-anomalies="state.isAnomalies"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchTickets()" />
          <template v-else>
            <div
              v-for="item of state.list"
              :key="item.id"
              class="ticket-side__item"
              :class="[{ 'ticket-side__item--active': state.activeTicket?.id === item.id }]"
              @click="handleSelected(item)">
              <div class="ticket-side__item-title">
                <strong
                  v-overflow-tips
                  class="ticket-side__item-name text-overflow">
                  {{ item.ticket_type_display }}
                </strong>
                <BkTag
                  class="ticket-side__item-tag"
                  :theme="item.getTagTheme()">
                  {{ $t(item.getStatusText()) }}
                </BkTag>
              </div>
              <div
                v-if="item.related_object"
                class="ticket-side__item-info is-single">
                <span class="info-item-label">{{ item.related_object.title }}：</span>
                <RenderRow
                  class="info-item-value"
                  :data="item.related_object.objects"
                  style="overflow: hidden;" />
              </div>
              <div class="ticket-side__item-info is-single">
                <span class="info-item-label">{{ $t('业务') }}：</span>
                <span
                  v-overflow-tips
                  class="info-item-value text-overflow">{{ item.bk_biz_name }}</span>
              </div>
              <div class="ticket-side__item-info">
                <span>{{ $t('申请人') }}： {{ item.creator }}</span>
                <span>{{ item.getFormatCreateAt() }}</span>
              </div>
            </div>
          </template>
        </BkLoading>
      </div>
      <BkPagination
        v-model="state.page.current"
        align="center"
        class="ticket-side__pagination"
        :count="state.page.total"
        :limit="state.page.limit"
        :show-total-count="false"
        small
        @change="handleChangePage" />
    </div>
  </div>
</template>

<script lang="ts">
  import TicketModel from '@services/model/ticket/ticket';
  import type { SearchFilterItem } from '@services/types/common';

  import type { SearchValue } from '@components/vue2/search-select/index.vue';
  /**
   * 列表基础数据
   */
  export interface TicketsState {
    list: TicketModel[],
    isLoading: boolean,
    isAnomalies: boolean,
    activeTicket: TicketModel | null,
    isInit: boolean,
    ticketTypes: Array<SearchFilterItem>,
    filters: {
      status: string,
      search: SearchValue[],
    },
    page: {
      current: number,
      limit: number,
      total: number,
    },
    bkBizIdList: Array<SearchFilterItem>,
  }
</script>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type StatusTypeKeys, StatusTypes } from '@services/model/ticket/ticket';
  import { getTickets, getTicketTypes } from '@services/ticket';

  import {
    useGlobalBizs,
  } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import ListTabs from './components/Tabs.vue';

  interface StatusItem {
    label: string,
    value: string
  }

  interface Emits {
    (e: 'change', value: TicketModel | null): void
  }

  const emits = defineEmits<Emits>();
  const currentScope = getCurrentScope();
  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  let isInitFetch = true;
  const state = reactive<TicketsState>({
    list: [],
    isLoading: false,
    isAnomalies: false,
    activeTicket: null,
    isInit: false,
    filters: {
      status: 'ALL',
      search: [],
    },
    page: {
      current: 1,
      limit: 20,
      total: 0,
    },
    ticketTypes: [],
    bkBizIdList: [],
  });
  const activeTab = ref('');
  const initId = computed(() => route.query.id);
  const filterId = computed(() => route.query.filterId);
  const isSearching = computed(() => state.filters.status !== 'ALL' || state.filters.search.length > 0);
  // 状态过滤列表
  const filters = Object.keys(StatusTypes).map((key: string) => ({
    label: t(StatusTypes[key as StatusTypeKeys]),
    value: key,
  }));
  const searchSelectData = computed(() => [{
    name: t('单号'),
    id: 'id',
  }, {
    name: t('业务'),
    id: 'bk_biz_id',
    children: state.bkBizIdList,
  }, {
    name: t('单据类型'),
    id: 'ticket_type__in',
    multiple: true,
    children: state.ticketTypes,
  }]);

  // 状态选择设置
  const isShowDropdown = ref(false);
  const activeItemInfo = computed(() => filters.find(item => item.value === state.filters.status));
  const handleToggle = () => {
    isShowDropdown.value = !isShowDropdown.value;
  };
  const handleClose = () => {
    isShowDropdown.value = false;
  };
  const handleChangeStatus = (item: StatusItem) => {
    state.filters.status = item.value;
    isShowDropdown.value = false;
    handleChangePage(1);
  };

  /**
   * 轮询列表
   */
  const { isActive, pause, resume } = useTimeoutPoll(() => {
    fetchTickets(true);
  }, 10000, { immediate: false });

  const handleClearSearch = () => {
    state.filters.status = 'ALL';
    state.filters.search = [];
    handleChangePage(1);
  };

  const handleChangeTab = (tab: string) => {
    activeTab.value = tab;
    if (isInitFetch === false) {
      state.filters.status = 'ALL';
      state.filters.search = [];
      handleChangePage(1);
      return;
    }
    nextTick(fetchTickets);
  };

  onMounted(() => {
    getBizIdList();
    fetchTicketTypes();

    state.page.current = route.query.current ? Number(route.query.current) : 1;
    state.page.limit =  route.query.limit ? Number(route.query.limit) : 20;

    // 任务历史跳转过来需要过滤出对应单据。
    if (filterId.value) {
      state.filters.search.push({
        name: t('单号'),
        id: 'id',
        values: [{
          id: filterId.value as string,
          name: filterId.value as string,
        }],
      });
    }
  });

  watch(() => state.activeTicket, () => {
    emits('change', state.activeTicket);
  });

  /**
   * 视图定位到激活项
   */
  const sideListRef = ref<HTMLDivElement>();
  function activeItemScrollIntoView() {
    if (sideListRef.value) {
      const activeItem = sideListRef.value.querySelector('.ticket-side__item--active');
      if (activeItem) {
        activeItem.scrollIntoView();
      }
    }
  }

  /**
   * 获取单据类型
   */
  function fetchTicketTypes() {
    return getTicketTypes().then((res) => {
      state.ticketTypes = res.map(item => ({
        id: item.key,
        name: item.value,
      }));
      return state.ticketTypes;
    });
  }

  /**
   * 获取业务列表
   */
  function getBizIdList() {
    state.bkBizIdList = globalBizsStore.bizs.map(item => ({
      id: item.bk_biz_id,
      name: item.name,
    }));
    return state.bkBizIdList;
  }

  /**
   * 获取单据列表
   */
  function fetchTickets(isPoll = false) {
    state.isLoading = !isPoll;
    if (sideListRef.value) {
      sideListRef.value.scrollTop = 0;
    }
    const params = {
      self_manage: activeTab.value === 'all' ? 1 : 0,
      status: state.filters.status === 'ALL' ? '' : state.filters.status,
      limit: state.page.limit,
      offset: (state.page.current - 1) * state.page.limit,
      ...getSearchSelectorParams(state.filters.search),
    };
    getTickets(params)
      .then((res) => {
        const { results = [], count = 0 } = res;
        state.list = results;
        state.page.total = count;

        if (currentScope?.active) {
          isActive.value === false && resume();
        } else {
          pause();
        }

        if (isPoll) return;

        if (results.length > 0) {
          // 刷新界面自动选中
          const id = initId.value || filterId.value;
          const activeItem = results.find(item => item.id === Number(id));
          if (activeItem) {
            state.activeTicket = activeItem;
          } else {
            // 默认选中第一条
            [state.activeTicket] = results;
          }
          nextTick(() => {
            activeItemScrollIntoView();
          });
        } else {
          state.activeTicket = null;
        }
        state.isAnomalies = false;
      })
      .catch(() => {
        state.list = [];
        state.page.total = 0;
        state.isAnomalies = true;
      })
      .finally(() => {
        isInitFetch = false;
        state.isLoading = false;
        // 任务历史跳转过来过滤完成后需要清空，不影响列表操作
        if (filterId.value) {
          router.replace({ query: { filterId: undefined } });
        }
      });
  }

  /**
   * 翻页
   * @param page
   */
  function handleChangePage(page = 1) {
    if (isInitFetch) return;
    state.page.current = page;
    pause();
    nextTick(() => {
      fetchTickets();
    });
  }

  /**
   * 选中单据
   */
  function handleSelected(data: TicketModel) {
    state.activeTicket = data;
    router.replace({
      query: {
        limit: state.page.limit,
        current: state.page.current,
        id: data.id,
      },
    });
  }
</script>

<style lang="less" scoped>
@import "@/styles/mixins.less";

.ticket-side {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: 320px;
  height: 100%;
  background-color: @white-color;

  &__top {
    flex-shrink: 0;
    padding: 16px;
    border-bottom: 1px solid @border-disable;
  }

  &__header {
    .flex-center();

    justify-content: space-between;
    padding-bottom: 8px;
    color: @title-color;
  }

  .status-trigger {
    position: relative;
    height: 32px;
    padding: 0 24px 0 10px;
    font-size: 12px;
    line-height: 32px;
    color: @default-color;
    cursor: pointer;
    background-color: #fff;

    .status-trigger-icon {
      position: absolute;
      right: 6px;
      font-size: 14px;
      line-height: 32px;
      color: @gray-color;
      transition: all 0.3s;
    }

    &:hover,
    &.is-active {
      background-color: #f5f7fa;
    }

    &.is-active {
      .status-trigger-icon {
        transform: rotate(180deg);
      }
    }
  }

  &__main {
    width: 100%;
    flex: 1;
    min-height: 0;
  }

  &__list {
    width: 100%;
    height: calc(100% - 32px);

    .bk-nested-loading {
      width: 100%;
      height: 100%;
    }
  }

  &__item {
    padding: 16px;
    font-size: @font-size-mini;
    cursor: pointer;
    border-bottom: 1px solid @border-disable;

    &:hover,
    &--active {
      background-color: @bg-gray;
    }

    &-title {
      display: flex;
      align-items: center;
      padding-bottom: 8px;
      overflow: hidden;
    }

    &-name {
      padding-right: 8px;
    }

    &-tag {
      flex-shrink: 0;
    }

    &-info {
      .flex-center();

      justify-content: space-between;

      &.is-single {
        justify-content: flex-start;
        margin-bottom: 8px;
      }

      .info-item-label {
        flex-shrink: 0;
      }

      .info-item-value {
        flex-grow: 1;

        :deep(.bk-tag) {
          height: 16px;
          padding: 0 4px;
          margin: 0;
          line-height: 16px;
        }
      }
    }
  }

  &__pagination {
    padding: 2px 0;

    :deep(.bk-pagination-limit) {
      display: none;
    }
  }
}
</style>
