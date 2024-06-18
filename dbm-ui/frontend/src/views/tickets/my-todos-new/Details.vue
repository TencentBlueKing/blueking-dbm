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
  <Teleport to="#dbContentHeaderAppend">
    <div
      ref="subTitleRef"
      class="head-tag">
      {{ t('Redis 集群申请') }}
    </div>
  </Teleport>
  <BkResizeLayout
    :border="false"
    :initial-divide="400"
    :max="600"
    :min="400"
    placement="left">
    <template #aside>
      <div class="ticket-manage-list">
        <div class="filter-box">
          <div class="filter-menu">
            <BkDropdown
              :is-show="isShowDropdown"
              trigger="manual"
              @hide="handleClose">
              <div
                class="dropdown-trigger"
                :class="{ 'dropdown-trigger-active': isShowDropdown }"
                @click="handleToggle">
                <span>{{ menuActive.label }} ( {{ menuActive.count }} ) </span>
                <DbIcon
                  class="down-shape"
                  type="bk-dbm-icon db-icon-down-shape dropdown-trigger-icon" />
              </div>
              <template #content>
                <BkDropdownMenu class="dropdown-menu">
                  <BkDropdownItem
                    v-for="item in menuItems"
                    :key="item.name"
                    class="dropdown-item"
                    :class="{ 'dropdown-item-active': item.name === menuActive.name }"
                    @click="handleChangeMenu(item)">
                    {{ item.label }} ( {{ item.count }} )
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
            <BkButton
              class="ml-8"
              theme="primary"
              @click="handleClickBatch">
              {{ buttonText }}
            </BkButton>
          </div>
          <div class="filter-search">
            <DbSearchSelect
              v-model="state.filters.search"
              class="search-bar"
              :data="searchSelectData"
              :placeholder="t('请输入或选择条件搜索')"
              unique-select
              @change="handleSearchChange" />
            <BkCheckbox
              class="check-all ml-10"
              :indeterminate="isIndeterminate"
              :model-value="state.isSelectedAll"
              @change="handleSelectedAll">
              {{ t('全选') }}
            </BkCheckbox>
          </div>
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
                  @click="handleClickItem(item)">
                  <div class="side-item-title">
                    <div>
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
                    <BkCheckbox
                      :model-value="state.checkedMap[item.id]"
                      @change="handleSelectedOne(item)" />
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
    <template #main> </template>
  </BkResizeLayout>
</template>
<script lang="ts">
  import TicketModel from '@services/model/ticket/ticket';
  import type { SearchFilterItem } from '@services/types';

  import type { SearchValue } from '@components/vue2/search-select/index.vue';

  import { getTickets } from '@/services/source/ticket';
  import { useGlobalBizs } from '@/stores';
  import { getSearchSelectorParams } from '@/utils';
  /**
   * 列表基础数据
   */
  export interface TicketsState {
    list: TicketModel[];
    isLoading: boolean;
    isAnomalies: boolean;
    activeTicket: TicketModel<unknown> | null;
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
    checkedMap: Record<number, boolean>;
    selection: TicketModel[];
    isSelectedAll: boolean;
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderRow from '@components/render-row/index.vue';

  import { type PanelListItem } from './components/PanelTab.vue';

  enum TabNames {
    APPROVAL = 'approval',
    CONFIRM = 'confirm',
    REPLENISH = 'replenishment',
  }

  const { t } = useI18n();
  // const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const isBizTicketManagePage = route.name === 'bizTicketManage';
  const isSelfManage = route.query.self_manage === '1';

  const needPollIds: {
    index: number,
    id: number,
  }[] = [];
  const initMenuItems = [
    { name: TabNames.APPROVAL, label: t('待我审批'), count: 0 },
    { name: TabNames.CONFIRM, label: t('待我确认'), count: 0 },
    { name: TabNames.REPLENISH, label: t('待我补货'), count: 0 },
  ];
  const menuActive = ref<PanelListItem>(initMenuItems[0]);
  const menuItems = shallowRef<PanelListItem[]>(initMenuItems);
  const isShowDropdown = ref(false);
  // 视图定位到激活项
  const sideListRef = ref<HTMLDivElement>();
  const selfManage = ref<'0'|'1'>(isSelfManage ? '1' : '0');
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
    bkBizIdList: globalBizsStore.bizs.map((item) => ({
      id: item.bk_biz_id,
      name: item.name,
    })),
    checkedMap: {},
    selection: [],
    isSelectedAll: false,
  });
  const buttonText = computed(() => t(`批量${menuActive.value.label.slice(2)}`));
  const isSearching = computed(() => state.filters.status !== 'ALL' || state.filters.search.length > 0);
  const isIndeterminate = computed(()=> {
    const keysLen = Object.entries(state.checkedMap).filter(([_, value]) => value).length
    return keysLen < state.list.length && keysLen > 0
  })
  const searchSelectData = computed(() =>
    [
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
    ].filter((_) => _),
  );
  const getTabCount = async () => {
    // const res = await getTicketTypeCount()
    // local mock、、代接口开发后删掉即可
    const res: Record<TabNames, number> = {
      approval: 100,
      confirm: 20,
      replenishment: 0,
    };
    const newPanels: PanelListItem[] = ([...menuItems.value] as PanelListItem[]).reduce((result, item) => {
      const count = res[item.name as TabNames];
      result.push({ ...item, count });
      return result;
    }, [] as PanelListItem[]);
    menuItems.value = newPanels;
    const [first] = newPanels;
    if (first) menuActive.value = first as PanelListItem;
  };
  getTabCount();
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

          handleClickItem(state.activeTicket);

          nextTick(() => {
            if (sideListRef.value) {
              const activeItem = sideListRef.value.querySelector('.side-item-active');
              if (activeItem) {
                activeItem.scrollIntoView();
              }
            }
          });
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
  const handleChangeMenu = (item: PanelListItem) => {
    menuActive.value = item;
    isShowDropdown.value = false;
  };
  const handleToggle = () => {
    isShowDropdown.value = !isShowDropdown.value;
  };
  const handleClose = () => {
    isShowDropdown.value = false;
  };
  const handleClearSearch = () => {
    state.filters.status = 'ALL';
    state.filters.search = [];
    handleChangePage(1);
  };
  /**
   * 点击单据查看详情
   */
  const handleClickItem = (data: TicketModel<unknown>) => {
    state.activeTicket = data;
    // router.replace({
    //   query: {
    //     ...route.query,
    //     limit: state.page.limit,
    //     current: state.page.current,
    //     id: data.id,
    //     self_manage: selfManage.value,
    //   },
    // });
    // emits('change', state.activeTicket);
  };
  /**
   * 全选单据
   */
  const handleSelectedAll = () => {
    const currentIsSelectedAll = !state.isSelectedAll
    state.isSelectedAll = currentIsSelectedAll
    const result = currentIsSelectedAll ? [...state.list] : []
    state.selection = result;
    const checkedMap: Record<number, boolean> = {}
    result.forEach(item=> {
      checkedMap[item.id] = currentIsSelectedAll
    })
    state.checkedMap = checkedMap;

    console.log(currentIsSelectedAll, 'state.list', result, checkedMap);
  };
  /**
   * 单选单据
   */
  const handleSelectedOne = (data: TicketModel<unknown>) => {
    state.checkedMap[data.id] = !state.checkedMap[data.id]
  };
  const handleClickBatch = () => {
    console.log(state.selection);
  }
</script>

<style lang="less">
  .head-tag {
    position: relative;
    top: 2px;
    padding: 1px 8px;
    margin-left: 9px;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    text-align: center;
    background: #f0f1f5;
    border-radius: 2px;
  }

  .dropdown-menu {
    width: 256px;

    .dropdown-item {
      font-size: 14px;
      color: #63656e;
    }
  }

  .ticket-manage-list {
    position: relative;
    z-index: 100;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    height: 100%;
    background-color: @white-color;
    box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);

    .filter-box {
      flex-shrink: 0;
      padding: 16px 24px;
      border-bottom: 1px solid @border-disable;
    }

    .filter-menu {
      display: flex;
      margin-bottom: 16px;

      .bk-dropdown {
        flex: 1;
      }

      .dropdown-trigger {
        display: flex;
        height: 32px;
        padding: 6px 13px 7px 16px;
        font-size: 14px;
        color: #63656e;
        cursor: pointer;
        background: #f0f1f5;
        border-radius: 2px;
        justify-content: space-between;
        align-items: center;

        .dropdown-trigger-icon {
          font-size: 12px;
          line-height: 32px;
          color: @gray-color;
          transition: all 0.3s;
        }
      }

      .dropdown-trigger-active {
        .dropdown-trigger-icon {
          transform: rotate(180deg);
        }
      }
    }

    .filter-search {
      display: flex;

      .search-bar {
        flex: 1;
      }

      .check-all {
        display: flex;
        width: 88px;
        height: 32px;
        background: #f5f7fa;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }
    }

    .side-main {
      width: 100%;
      flex: 1;
      min-height: 0;
    }

    .side-list {
      width: 100%;
      height: calc(100vh - 250px);

      .bk-nested-loading {
        width: 100%;
        height: 100%;
      }
    }

    .side-item {
      padding: 16px 24px;
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
        justify-content: space-between;
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
        display: flex;
        align-items: center;
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
