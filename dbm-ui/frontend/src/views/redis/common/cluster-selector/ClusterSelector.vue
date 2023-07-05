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
    :is-show="props.isShow"
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
                  :key="item.immute_domain"
                  class="result__item">
                  <span
                    v-overflow-tips
                    class="text-overflow">{{ item.immute_domain }}</span>
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
              placeholder="请输入集群域名/集群别名进行搜索"
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
                @page-limit-change="handleTableLimitChange"
                @page-value-change="handleTablePageChange"
                @refresh="fetchResources"
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

  import { useCopy, useDefaultPagination } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { messageWarn } from '@utils';

  import CollapseMini from './CollapseMini.vue';
  import type { ClusterSelectorResult, ClusterSelectorState } from './types';
  import { useClusterData } from './useClusterData';

  import RedisModel from '@/services/model/redis/redis';

  interface Props {
    isShow: boolean;
    selected: ClusterSelectorResult;
    tabList: Array<string>
  }

  interface Emits {
    (e: 'update:is-show', value: boolean): void;
    (e: 'change', value: ClusterSelectorResult): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    selected: () => ({ [ClusterTypes.REDIS]: [] }),
    tabList: () => [ClusterTypes.REDIS],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // const { currentBizId } = useGlobalBizs();

  let rawTableData: RedisModel[] = [];

  function initData() {
    const clusterType = ClusterTypes.REDIS;
    return {
      curSelectdDataTab: clusterType,
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
      isSelectedAll: false,
      dbModuleList: [],
      isAnomalies: false,
    };
  }

  const handleClickSearch = async () => {
    console.log('key word: ', state.search);
    const keyword = state.search;
    if (rawTableData.length === 0) rawTableData = [...state.tableData];
    if (keyword) {
      const filterList = state.tableData.filter(item => item.immute_domain.includes(keyword)
        || item.alias.includes(keyword));
      state.tableData = filterList;
    } else {
      handleClickClearSearch();
    }
  };

  const handleClickClearSearch = () => {
    state.tableData = rawTableData;
  };

  // 显示切换 tab tips
  const showSwitchTabTips = computed(() => tabState.showTips);
  const state = reactive<ClusterSelectorState>(initData());
  // 已选值 keys
  const selectedKeys = computed(() => Object.keys(state.selected));
  // 选中结果是否为空
  const isEmpty = computed(() => !selectedKeys.value.some(key => state.selected[key].length));

  // 选中域名列表
  const selectedDomains = computed(() => (state.selected[state.activeTab] || []).map(item => item.immute_domain));
  const columns = [{
    width: 60,
    label: () => (
      <bk-checkbox
        key={`${state.pagination.current}_${state.activeTab}`}
        model-value={state.isSelectedAll}
        label={true}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={handleSelectedAll}
      />
    ),
    render: ({ data }: { data: RedisModel }) => (
      <bk-checkbox
        style="vertical-align: middle;"
        model-value={selectedDomains.value.includes(data.immute_domain)}
        label={true}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={handleSelected.bind(null, data)}
      />
    ),
  }, {
    label: t('集群'),
    field: 'immute_domain',
    showOverflowTooltip: true,
  }, {
    label: t('状态'),
    field: 'master_domain',
    showOverflowTooltip: true,
    minWidth: 100,
    render: ({ data }: { data: RedisModel }) => {
      const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  }, {
    label: t('集群别名'),
    field: 'alias',
    showOverflowTooltip: true,
  }, {
    label: t('所属云区域'),
    field: 'region',
    render: ({ data }: { data: RedisModel }) => data.cloud_info.bk_cloud_name,
  }];

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
  // 获取 tab 信息
  function getTabInfo(key: string) {
    return tabs.value.find(tab => tab.id === key);
  }
  /**
   * 切换 tab
   */
  function handleChangeTab(id: string) {
    if (state.activeTab === id) return;

    state.activeTab = id;
  }
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

  const {
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useClusterData(state);

  watch(() => props.isShow, (show) => {
    if (show) {
      state.selected = _.cloneDeep(props.selected);
      tabState.showTips = true;
      handleTablePageChange(1);
    }
  });

  watch(() => state.activeTab, () => {
    state.search = '';
    handleTablePageChange(1);
  });

  /**
   * 清空过滤列表
   */
  function handleClearSearch() {
    state.search = '';
    nextTick(() => {
      handleTablePageChange(1);
    });
  }

  function isSelectedAll() {
    if (selectedDomains.value.length === 0) return false;

    const diff = _.differenceBy(state.tableData, selectedDomains.value.map(item => ({ immute_domain: item })), 'immute_domain');
    return diff.length === 0;
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
   * 选择当行数据
   */
  function handleSelected(data: RedisModel, value: boolean) {
    // console.log('select: ', data, value);

    const targetValue = data.immute_domain;
    const index = selectedDomains.value.findIndex(val => val === targetValue);
    if (value && index === -1) {
      state.selected[state.activeTab].push(data);
    } else if (!value && index > -1) {
      state.selected[state.activeTab].splice(index, 1);
    }

    state.isSelectedAll = isSelectedAll();
  }

  function handleRowClick(_:any, data: RedisModel) {
    const index = selectedDomains.value.findIndex(val => val === data.immute_domain);
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
    state.isSelectedAll = false;
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
      copyValues.push(...state.selected[key].map(item => item.immute_domain));
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

  function handleTablePageChange(value: number) {
    handleChangePage(value).then(() => {
      state.isSelectedAll = isSelectedAll();
    });
  }

  function handleTableLimitChange(value: number) {
    handeChangeLimit(value).then(() => {
      state.isSelectedAll = isSelectedAll();
    });
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
@/services/model/redis/redis
