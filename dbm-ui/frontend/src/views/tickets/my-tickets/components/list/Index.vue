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
        <div style="font-weight: bold">{{ t('申请列表') }}</div>
        <TicketStatus v-model="ticketStatus" />
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
        v-model="searachSelectValue"
        :data="searchSelectData"
        :placeholder="searchPlaceholder"
        unique-select />
    </div>
    <div class="side-main">
      <div
        ref="sideListRef"
        class="side-list db-scroll-y">
        <BkLoading :loading="isLoading">
          <EmptyStatus
            v-if="list.length === 0"
            :is-anomalies="isAnomalies"
            :is-searching="isSearching"
            @clear-search="handleClearSearch"
            @refresh="fetchTicketList" />
          <template v-else>
            <div
              v-for="item of list"
              :key="item.id"
              class="side-item"
              :class="[{ 'side-item-active': modelValue === item.id }]"
              @click="handleChange(item.id)">
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
        v-model="pagination.current"
        align="center"
        class="side-pagination"
        :count="pagination.total"
        :limit="pagination.limit"
        :show-total-count="false"
        small
        @change="handlePaginationChange" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getTickets, getTicketTypes } from '@services/source/ticket';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';
  import type { SearchValue } from '@components/vue2/search-select/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import TicketStatus from './components/TicketStatus.vue';

  const { t } = useI18n();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const { replaceSearchParams } = useUrlSearch();

  const isBizTicketManagePage = route.name === 'bizTicketManage';
  const searchPlaceholder = isBizTicketManagePage ? t('单号_单据类型_申请人') : t('单号_单据类型_业务');

  const modelValue = defineModel<number>();

  const sideListRef = ref<HTMLDivElement>();
  const isAnomalies = ref(false);
  const searachSelectValue = ref<SearchValue[]>([]);
  const selfManage = ref<'0' | '1'>(route.query.self_manage === '1' ? '1' : '0');
  const ticketStatus = ref(route.query.status || 'ALL');
  const list = ref<ServiceReturnType<typeof getTickets>['results']>([]);
  const ticketTypeList = shallowRef<{ id: string; name: string }[]>([]);

  const pagination = reactive({
    current: route.query.offset ? Math.ceil(Number(route.query.offset) / 20) + 1 : 1,
    limit: route.query.limit ? Number(route.query.limit) : 20,
    total: 0,
  });

  const searchSelectData = computed(() =>
    [
      {
        name: t('单号'),
        id: 'id',
      },
      !isBizTicketManagePage && {
        name: t('业务'),
        id: 'bk_biz_id',
        children: globalBizsStore.bizs.map((item) => ({
          id: item.bk_biz_id,
          name: item.name,
        })),
      },
      {
        name: t('单据类型'),
        id: 'ticket_type__in',
        multiple: true,
        children: ticketTypeList.value,
      },
      isBizTicketManagePage && {
        name: t('申请人'),
        id: 'creator',
      },
    ].filter((_) => _),
  );

  const isSearching = computed(() => ticketStatus.value !== 'ALL' || searachSelectValue.value.length > 0);

  useRequest(getTicketTypes, {
    onSuccess(data) {
      ticketTypeList.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  const getFetchTicketsParams = () => {
    const params = {
      status: ticketStatus.value === 'ALL' ? '' : (ticketStatus.value as string),
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      ...getSearchSelectorParams(searachSelectValue.value),
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
    return params;
  };

  const { run: fetchTicketListStatus } = useRequest(
    () => {
      const params = getFetchTicketsParams();
      return getTickets(params);
    },
    {
      onSuccess(data) {
        list.value = data.results;
      },
    },
  );
  /**
   * 获取单据列表
   */
  const { loading: isLoading, run: fetchTicketList } = useRequest(
    () => {
      const params = getFetchTicketsParams();
      return getTickets(params);
    },
    {
      onSuccess(data) {
        const { results = [], count = 0 } = data;
        list.value = results;
        pagination.total = count;

        nextTick(() => {
          sideListRef.value!.scrollTop = 0;
          if (results.length > 0) {
            const activeItem = sideListRef.value!.querySelector('.side-item-active');
            if (activeItem) {
              activeItem.scrollIntoView();
            } else {
              handleChange(results[0].id);
            }
          }
        });

        setTimeout(() => {
          fetchTicketListStatus();
        }, 10000);

        replaceSearchParams({
          ...getFetchTicketsParams(),
        });

        isAnomalies.value = false;
      },
      onError() {
        isAnomalies.value = true;
      },
    },
  );

  watch(
    [selfManage, ticketStatus, searachSelectValue],
    () => {
      pagination.current = 1;
      fetchTicketList();
    },
    {
      deep: true,
    },
  );

  const handlePaginationChange = (value: number) => {
    pagination.current = value;
    fetchTicketList();
  };

  const handleClearSearch = () => {
    ticketStatus.value = 'ALL';
    searachSelectValue.value = [];
  };

  const handleChange = (ticketId: number) => {
    modelValue.value = ticketId;
  };
</script>
<style lang="less">
  @import '@/styles/mixins.less';

  .ticket-manage-list {
    position: relative;
    z-index: 100;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    width: 320px;
    height: 100%;
    background-color: @white-color;
    box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);

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
