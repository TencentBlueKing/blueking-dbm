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
  <BkDialog
    class="cluster-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    height="auto"
    :is-show="isShow"
    :quick-close="false"
    title=""
    :width="1400"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      :initial-divide="400"
      :max="500"
      :min="300"
      placement="right">
      <template #aside>
        <div class="cluster-selector__result">
          <div class="result__title">
            <span>{{ $t('结果预览') }}</span>
            <BkDropdown class="result__dropdown">
              <i class="db-icon-more result__trigger" />
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleClearSelected">
                    {{ $t('清空所有') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopyCluster">
                    {{ $t('复制所有集群') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </div>
          <BkException
            v-if="isEmpty"
            class="mt-50"
            :description="$t('暂无数据_请从左侧添加对象')"
            scene="part"
            type="empty" />
          <template v-else>
            <template
              v-for="key in selectedKeys"
              :key="key">
              <CollapseMini
                v-if="state.selected[key].length > 0"
                collapse
                :count="state.selected[key].length"
                :title="getTabInfo(key)?.name">
                <div
                  v-for="item of state.selected[key]"
                  :key="item.prod_cluster"
                  class="result__item">
                  <span
                    v-overflow-tips
                    class="text-overflow">{{ item.prod_cluster }}</span>
                  <i
                    class="db-icon-close result__remove"
                    @click="handleSelected(item, false)" />
                </div>
              </CollapseMini>
            </template>
          </template>
        </div>
      </template>
      <template #main>
        <div class="cluster-selector__main">
          <div
            ref="clusterTabsRef"
            class="cluster-selector__tabs">
            <BkPopover
              v-for="item of tabs"
              :key="item.id"
              ref="tabTipsRef"
              :disabled="!showSwitchTabTips"
              theme="light">
              <div
                class="tabs__item tabs__item--active"
                @click.stop="handleChangeTab(item.id)">
                {{ item.name }}
              </div>
              <template #content>
                <div class="tab-tips">
                  <h4>{{ $t('切换类型说明') }}</h4>
                  <p>{{ $t('切换后如果重新选择_选择结果将会覆盖原来选择的内容') }}</p>
                  <BkButton
                    size="small"
                    theme="primary"
                    @click="handleCloseTabTips">
                    {{ $t('我知道了') }}
                  </BkButton>
                </div>
              </template>
            </BkPopover>
          </div>
          <div class="cluster-selector__content">
            <BkInput
              v-model="state.search"
              class="search-box"
              clearable
              :placeholder="$t('请输入访问入口/目标集群')"
              type="search"
              @clear="handleClickClearSearch"
              @enter="handleClickSearch" />
            <BkLoading
              :loading="state.isLoading"
              :z-index="2">
              <DbOriginalTable
                :columns="columns"
                :data="state.tableData"
                :height="500"
                :is-anomalies="state.isAnomalies"
                :is-searching="state.search !== ''"
                :pagination="{
                  ...state.pagination,
                  small: true
                }"
                remote-pagination
                row-style="cursor: pointer;"
                @clear-search="handleClearSearch"
                @page-limit-change="handeChangeLimit"
                @page-value-change="handleChangePage"
                @refresh="fetchHostNodes"
                @row-click.stop="handleRowClick" />
            </BkLoading>
          </div>
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        class="cluster-selector__button mr-8"
        :disabled="isEmpty"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        class="cluster-selector__button"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">

  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisRollbackModel from '@services/model/redis/redis-rollback';
  import { getRollbackList } from '@services/redis/toolbox';

  import { useCopy, useDefaultPagination } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import { encodeRegexp, messageWarn } from '@utils';

  import CollapseMini from './CollapseMini.vue';
  import type { VisitEntrySelectorResult, VisitEntrySelectorState } from './types';


  interface Props {
    isShow: boolean;
    selected: Record<string, RedisRollbackModel[]>;
    tabList: Array<string>
  }

  interface Emits {
    (e: 'update:is-show', value: boolean): void;
    (e: 'change', value: VisitEntrySelectorResult): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    selected: () => ({ [ClusterTypes.REDIS]: [] }),
    tabList: () => [ClusterTypes.REDIS],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let rawTableData: RedisRollbackModel[] = [];

  const handleClickSearch = async () => {
    const keyword = state.search;
    if (state.tableData.length === 0) return;
    if (rawTableData.length === 0) {
      rawTableData = [...state.tableData];
    }
    if (keyword) {
      const regex = new RegExp(encodeRegexp(keyword));
      const filterList = rawTableData.filter(item => regex.test(item.temp_cluster_proxy)
        || regex.test(item.prod_cluster));
      state.tableData = filterList;
      state.pagination.count = filterList.length;
    } else {
      handleClickClearSearch();
    }
  };

  const handleClickClearSearch = () => {
    state.tableData = rawTableData;
    state.pagination.count = rawTableData.length;
  };

  // 显示切换 tab tips
  const showSwitchTabTips = computed(() => tabState.showTips);
  const state = reactive<VisitEntrySelectorState>(initData());
  // 已选值 keys
  const selectedKeys = computed(() => Object.keys(state.selected));
  // 选中结果是否为空
  const isEmpty = computed(() => !selectedKeys.value.some(key => state.selected[key].length));

  // 选中域名列表
  const selectedDomains = computed(() => (state.selected[state.activeTab] || []).map(item => item.prod_cluster));

  const isSelectAll = computed(() => state.tableData.length > 0
    && state.tableData.length === Object.values(state.selected[state.activeTab]).length);

  const isIndeterminate = computed(() => !isSelectAll.value && state.selected[state.activeTab].length > 0);

  const columns = [
    {
      width: 60,
      label: () => (
      <bk-checkbox
        indeterminate={isIndeterminate.value}
        model-value={isSelectAll.value}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={handleSelectedAll}
      />
    ),
      render: ({ data }: { data: RedisRollbackModel }) => (
      <bk-checkbox
        style="vertical-align: middle;"
        model-value={selectedDomains.value.includes(data.prod_cluster)}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={handleSelected.bind(null, data)}
      />
    ),
    },
    {
      label: t('构造产物访问入口'),
      field: 'temp_cluster_proxy',
      showOverflowTooltip: true },
    {
      label: t('目标集群'),
      field: 'prod_cluster',
      showOverflowTooltip: true,
      minWidth: 100 },
    {
      label: t('构造到指定时间'),
      field: 'recovery_time_point',
      showOverflowTooltip: true,
    },
  ];

  /** tabs 功能 */
  const tabState = reactive({
    showTips: false,
  });
  const tabTextMap: Record<string, string> = {
    [ClusterTypes.REDIS]: t('集群选择'),
  };
  const tabs = computed(() => {
    const { tabList } = props;
    return tabList.map((id: string) => ({
      id,
      name: tabTextMap[id],
    }));
  });

  onMounted(() => {
    fetchHostNodes();
  });

  function initData() {
    const clusterType = ClusterTypes.REDIS;
    return {
      activeTab: clusterType,
      search: '',
      isLoading: false,
      pagination: {
        ...useDefaultPagination(),
        limit: 20,
        'limit-list': [20, 50, 100],
      },
      tableData: [],
      selected: _.cloneDeep(props.selected),
      isAnomalies: false,
    };
  }

  const handleChangePage = (value: number) => {
    state.pagination.current = value;
    fetchHostNodes();
  };

  const handeChangeLimit = (value: number) => {
    state.pagination.limit = value;
    state.pagination.current = 1;
    fetchHostNodes();
  };

  const fetchHostNodes = async () => {
    const ret = await getRollbackList({
      limit: state.pagination.limit,
      offset: state.pagination.current,
    });
    state.tableData = ret.results;
    state.pagination.count = ret.count;
  };

  // 获取 tab 信息
  const getTabInfo = (key: string) => tabs.value.find(tab => tab.id === key);
  /**
   * 切换 tab
   */
  const handleChangeTab = (id: string) => {
    if (state.activeTab === id) return;
    state.activeTab = id;
  };
  /**
   * 关闭提示
   */
  const tabTipsRef = ref();
  function handleCloseTabTips() {
    tabState.showTips = false;
    if (tabTipsRef.value) {
      for (const ref of tabTipsRef.value) {
        ref.hide();
      }
    }
  }


  watch(() => props.isShow, (show) => {
    if (show) {
      state.selected = _.cloneDeep(props.selected);
      tabState.showTips = true;
      handleChangePage(1);
    }
  });

  watch(() => state.activeTab, () => {
    state.search = '';
    handleChangePage(1);
  });

  /**
   * 清空过滤列表
   */
  function handleClearSearch() {
    state.search = '';
    nextTick(() => {
      handleChangePage(1);
    });
  }


  /**
   * 全选当页数据
   */
  function handleSelectedAll(value: boolean) {
    for (const data of state.tableData) {
      handleSelected(data, value);
    }
  }

  /**
   * 选择当前行数据
   */
  function handleSelected(data: RedisRollbackModel, value: boolean) {
    const targetValue = data.temp_cluster_proxy;
    if (value) {
      state.selected[state.activeTab].push(data);
    } else {
      const index = selectedDomains.value.findIndex(val => val === targetValue);
      state.selected[state.activeTab].splice(index, 1);
    }
  }

  function handleRowClick(_:number, data: RedisRollbackModel) {
    const index = selectedDomains.value.findIndex(val => val === data.temp_cluster_proxy);
    const checked = index > -1;
    handleSelected(data, !checked);
  }

  /**
   * 清空选中项
   */
  function handleClearSelected() {
    for (const key of selectedKeys.value) {
      state.selected[key] = [];
    }
  }

  /**
   * 复制集群域名
   */
  const copy = useCopy();
  function handleCopyCluster() {
    if (isEmpty.value) {
      messageWarn(t('没有可复制集群'));
      return;
    }

    const copyValues: Array<string> = [];
    for (const key of selectedKeys.value) {
      copyValues.push(...state.selected[key].map(item => item.prod_cluster));
    }
    copy(copyValues.join('\n'));
  }

  function handleConfirm() {
    emits('change', _.cloneDeep(state.selected));
    handleClose();
  }

  function handleClose() {
    emits('update:is-show', false);
  }

</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .cluster-selector {
    font-size: @font-size-mini;

    :deep(.bk-modal-header) {
      display: none;
    }

    :deep(.bk-modal-content) {
      padding: 0;
    }

    &__tabs {
      height: 42px;
      font-size: @font-size-mini;
      line-height: 42px;
      background-color: #fafbfd;
      border-bottom: 1px solid @border-disable;
      .flex-center();

      .tabs__item {
        min-width: 200px;
        margin-bottom: -1px;
        text-align: center;
        cursor: pointer;
        border: 1px solid @border-disable;
        border-top: 0;
        border-left: 0;
        border-bottom-color: transparent;

        &--active {
          background-color: @bg-white;
          border-bottom-color: @border-white;
        }
      }
    }

    &__content {
      height: 585px;
      padding: 16px 24px 0;

      .search-box {
        margin-bottom: 14px;
      }

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }
    }

    &__result {
      height: 100%;
      padding: 12px 24px;
      font-size: @font-size-mini;
      background-color: #f5f6fa;

      .result__title {
        padding-bottom: 16px;
        .flex-center();

        > span {
          flex: 1;
          font-size: @font-size-normal;
          color: @title-color;
        }

        .result__dropdown {
          font-size: 0;
          line-height: 20px;
        }

        .result__trigger {
          display: block;
          font-size: 18px;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            background-color: @bg-disable;
            border-radius: 2px;
          }
        }
      }

      .result__item {
        padding: 0 12px;
        margin-bottom: 2px;
        line-height: 32px;
        background-color: @bg-white;
        border-radius: 2px;
        justify-content: space-between;
        .flex-center();

        .result__remove {
          display: none;
          font-size: @font-size-large;
          font-weight: bold;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            color: @default-color;
          }
        }

        &:hover {
          .result__remove {
            display: block;
          }
        }
      }
    }

    &__button {
      width: 88px;
    }
  }

  .tab-tips {
    padding: 9px 0 17px;
    color: @default-color;
    text-align: right;

    h4 {
      font-size: @font-size-large;
      font-weight: normal;
      color: @title-color;
      text-align: left;
    }

    p {
      padding: 8px 0 16px;
      text-align: left;
    }
  }
</style>
