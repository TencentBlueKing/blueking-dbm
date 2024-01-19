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
    :width="dialogWidth"
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
            <span>{{ t('结果预览') }}</span>
            <BkDropdown class="result__dropdown">
              <i class="db-icon-more result__trigger" />
              <template #content>
                <BkDropdownMenu>
                  <BkDropdownItem @click="handleClearSelected">
                    {{ t('清空所有') }}
                  </BkDropdownItem>
                  <BkDropdownItem @click="handleCopyCluster">
                    {{ t('复制所有集群') }}
                  </BkDropdownItem>
                </BkDropdownMenu>
              </template>
            </BkDropdown>
          </div>
          <Component
            :is="activePanelObj.resultContent"
            :display-key="activePanelObj.previewResultKey"
            :selected-map="selectedMap"
            :show-title="activePanelObj.showPreviewResultTitle"
            :tab-list="tabList"
            @delete-item="handleSelecteRow" />
        </div>
      </template>
      <template #main>
        <div class="cluster-selector__main">
          <div
            ref="clusterTabsRef"
            class="cluster-selector__tabs">
            <BkPopover
              v-for="tabItem of tabList"
              :key="tabItem.id"
              ref="tabTipsRef"
              :disabled="!showSwitchTabTips"
              theme="light">
              <div
                class="tabs__item"
                :class="[{ 'tabs__item--active': tabItem.id === activeTab }]"
                @click.stop="handleChangeTab(tabItem)">
                {{ tabItem.name }}
              </div>
              <template
                #content>
                <div class="tab-tips">
                  <h4>{{ t('切换类型说明') }}</h4>
                  <p>{{ t('切换后如果重新选择_选择结果将会覆盖原来选择的内容') }}</p>
                  <BkButton
                    size="small"
                    theme="primary"
                    @click="handleCloseTabTips">
                    {{ t('我知道了') }}
                  </BkButton>
                </div>
              </template>
            </BkPopover>
          </div>
          <div class="cluster-selector__content">
            <Component
              :is="activePanelObj.tableContent"
              :active-tab="activeTab"
              :column-status-filter="activePanelObj.columnStatusFilter"
              :custom-colums="activePanelObj.customColums"
              :disabled-row-config="activePanelObj.disabledRowConfig"
              :get-resource-list="activePanelObj.getResourceList"
              :search-placeholder="activePanelObj.searchPlaceholder"
              :search-select-list="activePanelObj.searchSelectList"
              :selected="selectedArr"
              @change="handleSelectTable" />
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
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="cluster-selector__button"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx" generic="T extends RedisModel | TendbhaModel | SpiderModel | MongodbModel">
  import _ from 'lodash';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import RedisModel from '@services/model/redis/redis';
  import SpiderModel from '@services/model/spider/spider';
  import { getMongoList } from '@services/source/mongodb';
  import { getRedisList } from '@services/source/redis';
  import { getSpiderList } from '@services/source/spider';
  import { getTendbhaList } from '@services/source/tendbha';
  import type { ListBase } from '@services/types';

  import { useCopy, useSelectorDialogWidth } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import { messageWarn } from '@utils';

  import { t } from '@locales/index';

  import ResultPreview from './components/common/result-preview/Index.vue';
  import type { SearchSelectList } from './components/common/SearchBar.vue';
  import MongoTable from './components/mongo/Index.vue';
  import RedisTable from './components/redis/Index.vue';
  import SpiderTable from './components/tendb-cluster/Index.vue';
  import TendbhaTable from './components/tendbha/Index.vue';

  export type TabListType = {
    name: string,
    id: ClusterTypes,
    // 不可选行及提示
    disabledRowConfig?: {
      handler: (data: any) => boolean,
      tip?: string,
    },
    // 自定义列
    customColums?: any[],
    // 结果预览使用的key
    previewResultKey?: string,
    // 搜索栏下拉选项
    searchSelectList?: SearchSelectList,
    // 搜索栏的placeholder
    searchPlaceholder?: string
    showPreviewResultTitle?: boolean,
    // 状态列
    columnStatusFilter?: (data: any) => boolean,
    // 查询接口
    getResourceList?: (params: any) => Promise<ListBase<Record<string, any>[]>>,
    tableContent: any,
    resultContent: any,
  }[];

  export type TabItem = TabListType[number];

  interface Props {
    selected: Record<string, T[]>,
    clusterTypes: ClusterTypes[],
    tabListConfig?: Record<string, TabConfig>,
    onlyOneType?: boolean,
  }

  interface Emits {
    (e: 'change', value: Props['selected']): void,
  }

  type TabConfig = Omit<TabItem, 'name' | 'id' | 'tableContent' | 'resultContent'>

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const tabListMap: Record<string, TabItem> = {
    [ClusterTypes.TENDBCLUSTER]: {
      id: ClusterTypes.TENDBCLUSTER,
      name: t('集群选择'),
      getResourceList: getSpiderList,
      tableContent: SpiderTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.REDIS]: {
      id: ClusterTypes.REDIS,
      name: t('集群选择'),
      getResourceList: getRedisList,
      tableContent: RedisTable,
      resultContent: ResultPreview,
      searchSelectList: [{
        name: t('集群'),
        id: 'domain',
      }, {
        name: t('集群别名'),
        id: 'name',
      }],
      searchPlaceholder: t('集群_集群别名'),
    },
    [ClusterTypes.TENDBHA]: {
      id: ClusterTypes.TENDBHA,
      name: t('集群选择'),
      getResourceList: getTendbhaList,
      tableContent: TendbhaTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.MONGO_REPLICA_SET]: {
      id: ClusterTypes.MONGO_REPLICA_SET,
      name: t('集群选择'),
      getResourceList: getMongoList,
      tableContent: MongoTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      id: ClusterTypes.MONGO_SHARED_CLUSTER,
      name: t('集群选择'),
      getResourceList: getMongoList,
      tableContent: MongoTable,
      resultContent: ResultPreview,
    },
  };

  const copy = useCopy();
  const { dialogWidth } = useSelectorDialogWidth();

  const tabTipsRef = ref();
  const activeTab = ref();
  const showTabTips = ref(false);
  const isSelectedAll = ref(false);
  const selectedMap = ref<Record<string, Record<string, T>>>({});

  const activePanelObj = shallowRef(tabListMap[ClusterTypes.TENDBCLUSTER]);

  const clusterTabListMap = computed<Record<string, TabItem>>(() => {
    if (props.tabListConfig) {
      Object.keys(props.tabListConfig).forEach((type) => {
        if (props.tabListConfig?.[type]) {
          tabListMap[type] = {
            ...tabListMap[type],
            ...props.tabListConfig[type],
          };
        }
      });
    }
    return tabListMap;
  });

  // eslint-disable-next-line max-len
  const tabList = computed(() => (props.clusterTypes ? props.clusterTypes.map(type => clusterTabListMap.value[type]) : []));

  const selectedArr = computed(() => (activeTab.value
    && selectedMap.value[activeTab.value] && (Object.keys(selectedMap.value).length > 0)
    ? ({ [activeTab.value]: Object.values(selectedMap.value[activeTab.value]) }) :  {}));

  // 显示切换 tab tips
  const showSwitchTabTips = computed(() => showTabTips.value && tabList.value.length > 1);
  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), item => Object.keys(item).length < 1));

  watch(() => props.clusterTypes, (types) => {
    if (types) {
      activePanelObj.value = clusterTabListMap.value[types[0]];
      [activeTab.value] = types;
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(isShow, (show) => {
    if (show && tabList.value) {
      selectedMap.value = tabList.value.map(item => item.id).reduce((result, tabKey) => {
        if (!props.selected[tabKey]) {
          return result;
        }
        const tabSelectMap = props.selected[tabKey].reduce((selectResult, selectItem) => ({
          ...selectResult,
          [selectItem.id]: selectItem,
        }), {} as Record<string, T>);
        return {
          ...result,
          [tabKey]: tabSelectMap,
        };
      }, {} as Record<string, Record<string, T>>);
      showTabTips.value = true;
    }
  });

  /**
   * 切换 tab
   */
  const handleChangeTab = (obj: TabItem) => {
    if (activeTab.value === obj.id) {
      return;
    }
    const currentTab = tabList.value.find(item => item.id === obj.id);
    activeTab.value = obj.id;
    if (currentTab) {
      activePanelObj.value = currentTab;
    }
  };

  /**
   * 关闭提示
   */
  const handleCloseTabTips = () => {
    showTabTips.value = false;
    if (tabTipsRef.value) {
      for (const ref of tabTipsRef.value) {
        ref.hide();
      }
    }
  };

  /**
   * 清空选中项
   */
  const handleClearSelected = () => {
    selectedMap.value = {};
    isSelectedAll.value = false;
  };

  /**
   * 复制集群域名
   */
  const handleCopyCluster = () => {
    const copyValues = Object.values(selectedMap.value).reduce((result, selectItem) => {
      result.push(...Object.values(selectItem).map(item => item.master_domain));
      return result;
    }, [] as string[]);

    if (copyValues.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }

    copy(copyValues.join('\n'));
  };

  const handleConfirm = () => {
    const result = Object.keys(selectedMap.value).reduce((result, tabKey) => ({
      ...result,
      [tabKey]: Object.values(selectedMap.value[tabKey]),
    }), {});
    emits('change', result);
    handleClose();
  };

  const handleClose = () => {
    isShow.value =  false;
  };

  /**
   * 选择当行数据
   */
  const handleSelecteRow = (data: T, value: boolean) => {
    const selectedMapMemo = { ...selectedMap.value };
    if (!selectedMapMemo[activeTab.value]) {
      selectedMapMemo[activeTab.value] = {};
    }
    if (value) {
      selectedMapMemo[activeTab.value][data.id] = data;
    } else {
      delete selectedMapMemo[activeTab.value][data.id];
    }
    selectedMap.value = selectedMapMemo;
  };

  const handleSelectTable = (selected: Record<string, Record<string, T>>) => {
    // 如果只允许选一种集群类型, 则清空非当前集群类型的选中列表
    // 如果是勾选的取消全选，则忽略
    if (props.onlyOneType && Object.keys(Object.values(selected)[0]).length > 0) {
      // 只会有一个key
      const [currentKey] = Object.keys(selected);
      Object.keys(selectedMap.value).forEach((key) => {
        if (key !== currentKey) {
          selectedMap.value[key] = {};
        } else {
          selectedMap.value[key] = selected[key];
        }
      });
      return;
    }
    Object.assign(selectedMap.value, selected);
  };
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
      height: 580px;
      padding: 16px 24px 0;

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
