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
  <div class="ticket-manage-list">
    <div class="filter-box">
      <div class="side-header">
        <strong>{{ t('申请列表') }}</strong>
        <BkDropdown
          :is-show="isShowDropdown"
          trigger="click"
          @hide="handleClose">
          <div
            class="status-trigger"
            :class="{ 'status-trigger-active': isShowDropdown }"
            @click="handleToggle">
            <span>{{ activeItemInfo?.label }}</span>
            <DbIcon type="down-big status-trigger-icon" />
          </div>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem
                v-for="item in filters"
                :key="item.value"
                :class="{ 'dropdown-item-active': item.value === state.filters.status }"
                @click="handleChangeStatus(item)">
                {{ item.label }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
      <BkTab
        v-if="!isBizTicketManagePage"
        v-model:active="selfManage"
        class="ticket-type-tab"
        type="card-tab">
        <BkTabPanel
          :label="t('我申请的')"
          name="0" />
        <BkTabPanel
          :label="t('与我相关的')"
          name="1" />
      </BkTab>
      <DbSearchSelect
        v-model="state.filters.search"
        :data="searchSelectData"
        :placeholder="searchPlaceholder"
        unique-select
        @change="handleSearchChange" />
    </div>
    <div class="side-main">
      <div
        ref="sideListRef"
        class="side-list db-scroll-y">
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
              class="side-item"
              :class="[{ 'side-item-active': state.activeTicket?.id === item.id }]"
              @click="handleSelected(item)">
              <div class="side-item-title">
                <strong
                  v-overflow-tips
                  class="side-item-name text-overflow">
                  {{ item.ticket_type_display }}
                </strong>
                <BkTag
                  class="side-item-tag"
                  :theme="item.tagTheme">
                  {{ t(item.statusText) }}
                </BkTag>
              </div>
              <div
                v-if="item.related_object"
                class="side-item-info is-single">
                <span class="info-item-label">{{ item.related_object.title }}：</span>
                <RenderRow
                  class="info-item-value"
                  :data="item.related_object.objects"
                  show-all
                  style="overflow: hidden" />
              </div>
              <div class="side-item-info is-single">
                <span class="info-item-label">{{ t('业务') }}：</span>
                <span
                  v-overflow-tips
                  class="info-item-value text-overflow">
                  {{ item.bk_biz_name }}
                </span>
              </div>
              <div class="side-item-info">
                <span>{{ t('申请人') }}： {{ item.creator }}</span>
                <span>{{ item.formatCreateAt }}</span>
              </div>
            </div>
          </template>
        </BkLoading>
      </div>
      <BkPagination
        v-model="state.page.current"
        align="center"
        class="side-pagination"
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
  import type { SearchFilterItem } from '@services/types';

  import type { SearchValue } from '@components/vue2/search-select/index.vue';
  /**
   * 列表基础数据
   */
  export interface TicketsState {
    list: TicketModel[];
    isLoading: boolean;
    isAnomalies: boolean;
    activeTicket: TicketModel | null;
    isInit: boolean;
    ticketTypes: Array<SearchFilterItem>;
    filters: {
      status: string;
      search: SearchValue[];
    };
    page: {
      current: number;
      limit: number;
      total: number;
    };
    bkBizIdList: Array<SearchFilterItem>;
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import {
    type StatusTypeKeys,
    StatusTypes,
  } from '@services/model/ticket/ticket';
  import {
    getTickets,
    getTicketTypes,
  } from '@services/source/ticket';

  import {
    useGlobalBizs,
  } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  interface Emits {
    (e: 'change', value: TicketModel | null): void
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const isBizTicketManagePage = route.name === 'bizTicketManage';
  const searchPlaceholder = isBizTicketManagePage ? t('单号_单据类型_申请人') : t('单号_单据类型_业务');

  const needPollIds: {
    index: number,
    id: number,
  }[] = [];
  // 状态过滤列表
  const filters = Object.keys(StatusTypes).map((key: string) => ({
    label: t(StatusTypes[key as StatusTypeKeys]),
    value: key,
  }));

  // 状态选择设置
  const isShowDropdown = ref(false);
  // 视图定位到激活项
  const sideListRef = ref<HTMLDivElement>();
  const selfManage = ref<'0'|'1'>('0');
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
      current: route.query.current ? Number(route.query.current) : 1,
      limit: route.query.limit ? Number(route.query.limit) : 20,
      total: 0,
    },
    ticketTypes: [],
    bkBizIdList: globalBizsStore.bizs.map(item => ({
      id: item.bk_biz_id,
      name: item.name,
    })),
  });

  const searchSelectData = computed(() => [
    {
      name: t('单号'),
      id: 'id',
    },
    !isBizTicketManagePage && {
      name: t('业务'),
      id: 'bk_biz_id',
      children: state.bkBizIdList,
    },
    {
      name: t('单据类型'),
      id: 'ticket_type__in',
      multiple: true,
      children: state.ticketTypes,
    },
    isBizTicketManagePage && {
      name: t('申请人'),
      id: 'creator',
    },
  ].filter(_ => _));

  const isSearching = computed(() => state.filters.status !== 'ALL' || state.filters.search.length > 0);

  const activeItemInfo = computed(() => filters.find(item => item.value === state.filters.status));

  /**
   * 获取单据列表
   */
  const fetchTickets = (isPoll = false) => {
    state.isLoading = !isPoll;
    if (sideListRef.value) {
      sideListRef.value.scrollTop = 0;
    }
    const params = {
      status: state.filters.status === 'ALL' ? '' : state.filters.status,
      limit: state.page.limit,
      offset: (state.page.current - 1) * state.page.limit,
      ...getSearchSelectorParams(state.filters.search),
    };
    if (isBizTicketManagePage) {
      Object.assign(params, {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      });
    } else {
      Object.assign(params, {
        self_manage: selfManage.value,
      });
    }

    getTickets(params)
      .then((res) => {
        const { results = [], count = 0 } = res;
        state.list = results;
        state.page.total = count;

        needPollIds.length = 0;
        results.forEach((item, index) => {
          if (item.status === 'RUNNING') {
            const obj = {
              index,
              id: item.id,
            };
            needPollIds.push(obj);
          }
        });

        if (isPoll) return;

        if (results.length > 0) {
          // 刷新界面自动选中
          // 默认选中第一条
          if (!state.activeTicket) {
            [state.activeTicket] = results;
          }

          nextTick(() => {
            if (sideListRef.value) {
              const activeItem = sideListRef.value.querySelector('.side-item-active');
              if (activeItem) {
                activeItem.scrollIntoView();
              }
            }
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
        state.isLoading = false;
      });
  };

  getTicketTypes()
    .then((res) => {
      state.ticketTypes = res.map(item => ({
        id: item.key,
        name: item.value,
      }));
    });

  watch(() => state.activeTicket, () => {
    emits('change', state.activeTicket);
  });

  watch(selfManage, () => {
    fetchTickets();
  });

  /**
   * 检查所有执行中的单据
   */
  const checkRunningTickets = async () => {
    if (needPollIds.length > 0) {
      const params = {
        status: state.filters.status === 'ALL' ? '' : state.filters.status,
        limit: state.page.limit,
        offset: (state.page.current - 1) * state.page.limit,
        ...getSearchSelectorParams(state.filters.search),
      };
      if (isBizTicketManagePage) {
        Object.assign(params, {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        });
      } else {
        Object.assign(params, {
          self_manage: selfManage.value,
        });
      }

      getTickets(params)
        .then((res) => {
          const { results = [] } = res;
          const statusMap = results.reduce((results, item) => {
            Object.assign(results, {
              [item.id]: item.status,
            });
            return results;
          }, {} as Record<string, string>);

          const needRemoveIndexs: number[] = [];
          needPollIds.forEach((item, index) => {
            const newStatus = statusMap[item.id] as StatusTypeKeys;
            if (newStatus && newStatus !== 'RUNNING' && state.list[item.index].status === 'RUNNING') {
              needRemoveIndexs.push(index);
              state.list[item.index].status = newStatus;
            }
          });
          if (needRemoveIndexs.length > 0) {
            needRemoveIndexs.forEach((index) => {
              needPollIds.splice(index, 1);
            });
          }
        });
    }
  };

  const handleSearchChange = () => {
    state.page.current = 1;
    fetchTickets();
  };
  /**
   * 翻页
   * @param page
   */
  const handleChangePage = (page = 1) => {
    state.page.current = page;
    fetchTickets();
  };

  const handleToggle = () => {
    isShowDropdown.value = !isShowDropdown.value;
  };

  const handleClose = () => {
    isShowDropdown.value = false;
  };

  const handleChangeStatus = (item: {label: string, value: string}) => {
    state.filters.status = item.value;
    isShowDropdown.value = false;
    handleChangePage(1);
  };

  const handleClearSearch = () => {
    state.filters.status = 'ALL';
    state.filters.search = [];
    handleChangePage(1);
  };
  /**
   * 选中单据
   */
  const handleSelected = (data: TicketModel) => {
    state.activeTicket = data;
    router.replace({
      query: {
        limit: state.page.limit,
        current: state.page.current,
        id: data.id,
      },
    });
  };

  /**
   * 轮询执行中的列表
   */
  const { resume } = useTimeoutPoll(() => {
    checkRunningTickets();
  }, 10000);

  resume();
</script>
<style lang="less">
  @import '@/styles/mixins.less';

  .ticket-manage-list {
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 320px;
    height: 100%;
    background-color: @white-color;

    .filter-box {
      flex-shrink: 0;
      padding: 16px;
      border-bottom: 1px solid @border-disable;

      .ticket-type-tab {
        margin-bottom: 12px;

        .bk-tab-header {
          width: 100%;
          height: 32px;
          font-size: 12px;
          line-height: 32px !important;
          border-radius: 2px;

          .bk-tab-header-nav {
            width: 100%;
            align-items: center;
          }

          .bk-tab-header-item {
            height: 24px;
            margin: 0 4px;
            line-height: 24px !important;
            border-radius: 2px;
            flex: 1;

            &:last-child::after {
              display: none;
            }

            &:not(:first-of-type)::before {
              left: -4px;
              display: block !important;
            }
          }
        }

        .bk-tab-content {
          display: none;
        }
      }

      .side-header {
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
      }

      .status-trigger:hover,
      .status-trigger-active {
        background-color: #f5f7fa;
      }

      .status-trigger-active {
        .status-trigger-icon {
          transform: rotate(180deg);
        }
      }
    }

    .side-main {
      width: 100%;
      flex: 1;
      min-height: 0;
    }

    .side-list {
      width: 100%;
      height: calc(100% - 32px);

      .bk-nested-loading {
        width: 100%;
        height: 100%;
      }
    }

    .side-item {
      padding: 16px;
      font-size: @font-size-mini;
      cursor: pointer;
      border-bottom: 1px solid @border-disable;

      .bk-tag {
        height: 16px;
        padding: 0 4px;
        margin: 0;

        .bk-tag-text {
          height: 16px;
          line-height: 16px;
          transform: scale(0.83, 0.83);
        }
      }

      .side-item-title {
        display: flex;
        align-items: center;
        padding-bottom: 8px;
        overflow: hidden;
      }

      .side-item-name {
        padding-right: 8px;
      }

      .side-item-tag {
        flex-shrink: 0;
      }

      .side-item-info {
        .flex-center();

        justify-content: space-between;

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

      .is-single {
        justify-content: flex-start;
        margin-bottom: 8px;
      }
    }

    .side-item:hover,
    .side-item-active {
      background-color: #ebf2ff;

      .side-item-title {
        .side-item-name {
          font-weight: 700;
          color: #313238;
        }

        .bk-tag {
          font-weight: 700;
        }
      }
    }

    .side-pagination {
      padding: 2px 0;

      .bk-pagination-limit {
        display: none;
      }
    }
  }
</style>
