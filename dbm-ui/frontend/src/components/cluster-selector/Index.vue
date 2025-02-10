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
    class="cluster-selector-dialog"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
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
        <div class="cluster-selector-result">
          <div class="result-title">
            <span>{{ t('结果预览') }}</span>
            <BkDropdown class="result-dropdown">
              <i class="db-icon-more result-trigger" />
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
            @delete="handleDeleteItem" />
        </div>
      </template>
      <template #main>
        <div
          ref="clusterTabsRef"
          class="cluster-selector-tabs">
          <BkPopover
            v-for="tabItem of tabList"
            :key="tabItem.id"
            ref="tabTipsRef"
            :disabled="!onlyOneType"
            theme="light">
            <div
              class="tabs-item"
              :class="[{ 'tabs-item-active': tabItem.id === activeTab }]"
              @click.stop="handleChangeTab(tabItem)">
              {{ tabItem.name }}
            </div>
            <template #content>
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
        <div class="cluster-selector-content">
          <Component
            :is="activePanelObj.tableContent"
            :active-tab="activeTab"
            :column-status-filter="activePanelObj.columnStatusFilter"
            :custom-colums="activePanelObj.customColums"
            :disabled-row-config="activePanelObj.disabledRowConfig"
            :get-resource-list="activePanelObj.getResourceList"
            :multiple="activePanelObj.multiple"
            :search-select-list="activePanelObj.searchSelectList"
            :selected="selectedMap[activeTab].list"
            @change="handleSelectTable" />
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <span class="mr24">
        <slot
          v-if="slots.submitTips"
          :cluster-list="selectedClusterList"
          name="submitTips" />
      </span>
      <span v-bk-tooltips="submitButtonDisabledInfo.tooltips">
        <BkButton
          class="cluster-selector-button mr-8"
          :disabled="submitButtonDisabledInfo.disabled"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="cluster-selector-button"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script
  setup
  lang="tsx"
  generic="
    T extends
      | RedisModel
      | TendbhaModel
      | TendbclusterModel
      | TendbsingleModel
      | MongodbModel
      | SqlServerHaModel
      | SqlServerSingleModel
  ">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import RedisModel from '@services/model/redis/redis';
  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getMongoList } from '@services/source/mongodb';
  import { getRedisList } from '@services/source/redis';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';
  import { getSingleClusterList } from '@services/source/sqlserverSingleCluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';
  import { getTendbsingleList } from '@services/source/tendbsingle';
  import type { ListBase } from '@services/types';

  import { useSelectorDialogWidth } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import { execCopy, messageWarn } from '@utils';

  import ResultPreview from './components/common/result-preview/Index.vue';
  import type { SearchSelectList } from './components/common/SearchBar.vue';
  import MongoTable from './components/mongo/Index.vue';
  import RedisTable from './components/redis/Index.vue';
  import SqlserverHaTable from './components/sqlserver-ha/Index.vue';
  import SqlserverSingleTable from './components/sqlserver-single/Index.vue';
  import SpiderTable from './components/tendb-cluster/Index.vue';
  import TendbSingleTable from './components/tendb-single/Index.vue';
  import TendbhaTable from './components/tendbha/Index.vue';

  export type TabListType = {
    name: string;
    id: string;
    tableContent: any;
    resultContent: any;
    // 不可选行及提示
    disabledRowConfig?: {
      handler: (data: any) => boolean;
      tip: string;
    }[];
    // 自定义列
    customColums?: any[];
    // 结果预览使用的key
    previewResultKey?: string;
    // 搜索栏下拉选项
    searchSelectList?: SearchSelectList;
    showPreviewResultTitle?: boolean;
    // 多选模式
    multiple?: boolean;
    // checkbox hover 提示
    checkboxHoverTip?: (data: any) => string;
    // 状态列
    columnStatusFilter?: (data: any) => boolean;
    // 查询接口
    getResourceList?: (params: any) => Promise<ListBase<Record<string, any>[]>>;
  }[];

  export type TabItem = TabListType[number];

  export type TabConfig = Omit<TabItem, 'tableContent' | 'resultContent'>;

  export interface SelectMapValueType<T> {
    [key: string]: {
      map: Record<string, T>;
      list: T[];
    };
  }

  export interface Props<T> {
    selected: Record<string, T[]>;
    clusterTypes: string[];
    tabListConfig?: Record<string, TabConfig>;
    onlyOneType?: boolean;
    supportOfflineData?: boolean;
    disableDialogSubmitMethod?: (hostList: Array<string>) => string | boolean;
  }

  export interface Emits<T> {
    (e: 'change', value: Props<T>['selected']): void;
  }

  const props = defineProps<Props<T>>();

  const emits = defineEmits<Emits<T>>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const slots = defineSlots<{
    submitTips?: () => VNode;
  }>();
  const { dialogWidth } = useSelectorDialogWidth();
  const { t } = useI18n();

  const tabListMap: Record<string, TabItem> = {
    [ClusterTypes.TENDBCLUSTER]: {
      id: ClusterTypes.TENDBCLUSTER,
      name: t('集群选择'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getTendbClusterList,
      tableContent: SpiderTable,
      resultContent: ResultPreview,
    },
    tendbclusterSlave: {
      id: 'tendbclusterSlave',
      name: t('集群选择'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getTendbClusterList,
      tableContent: SpiderTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.REDIS]: {
      id: ClusterTypes.REDIS,
      name: t('集群选择'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      getResourceList: getRedisList,
      tableContent: RedisTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.TENDBHA]: {
      id: ClusterTypes.TENDBHA,
      name: t('主从集群'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getTendbhaList,
      tableContent: TendbhaTable,
      resultContent: ResultPreview,
    },
    tendbhaSlave: {
      id: 'tendbhaSlave',
      name: t('主从集群'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getTendbhaSalveList,
      tableContent: TendbhaTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.TENDBSINGLE]: {
      id: ClusterTypes.TENDBSINGLE,
      name: t('单节点集群'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getTendbsingleList,
      tableContent: TendbSingleTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.MONGO_REPLICA_SET]: {
      id: ClusterTypes.MONGO_REPLICA_SET,
      name: t('副本集'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getMongoList,
      tableContent: MongoTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      id: ClusterTypes.MONGO_SHARED_CLUSTER,
      name: t('分片集群'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getMongoList,
      tableContent: MongoTable,
      resultContent: ResultPreview,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      id: ClusterTypes.SQLSERVER_SINGLE,
      name: t('SqlServer 单节点'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getSingleClusterList,
      tableContent: SqlserverSingleTable,
      resultContent: ResultPreview,
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      id: ClusterTypes.SQLSERVER_HA,
      name: t('SqlServer 主从'),
      disabledRowConfig: [
        {
          handler: (data: T) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      multiple: true,
      getResourceList: getHaClusterList,
      tableContent: SqlserverHaTable,
      resultContent: ResultPreview,
      showPreviewResultTitle: true,
    },
  };

  const tabTipsRef = ref();
  const activeTab = ref(ClusterTypes.TENDBCLUSTER as string);
  const showTabTips = ref(false);
  const isSelectedAll = ref(false);
  const selectedMap = ref<SelectMapValueType<T>>({});

  const activePanelObj = shallowRef(tabListMap[ClusterTypes.TENDBCLUSTER]);

  const clusterTabListMap = computed<Record<string, TabItem>>(() => {
    if (props.tabListConfig) {
      Object.keys(props.tabListConfig).forEach((type) => {
        if (props.tabListConfig?.[type]) {
          const disabledRowConfigList = props.supportOfflineData
            ? []
            : [
                {
                  handler: (data: T) => data.isOffline,
                  tip: t('集群已禁用'),
                },
              ];
          const disabledRowConfigProp = props.tabListConfig?.[type].disabledRowConfig;
          if (disabledRowConfigProp) {
            // 外部设置了 disabledRowConfig, 需要追加到 disabledRowConfig列表
            disabledRowConfigList.push(...disabledRowConfigProp);
          }
          tabListMap[type] = {
            ...tabListMap[type],
            ...props.tabListConfig[type],
            disabledRowConfig: disabledRowConfigList,
          };
        }
      });
    }
    return tabListMap;
  });

  const tabList = computed(() =>
    props.clusterTypes ? props.clusterTypes.map((type) => clusterTabListMap.value[type]) : [],
  );

  // 显示切换 tab tips
  // const showSwitchTabTips = computed(() => showTabTips.value && tabList.value.length > 1);
  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), (item) => Object.keys(item).length < 1));

  const selectedClusterList = computed(() =>
    Object.values(selectedMap.value).reduce<string[]>((prevList, selectedItem) => {
      const clusterList = selectedItem.list.map((clusterItem) => clusterItem.master_domain);
      prevList.push(...clusterList);
      return prevList;
    }, []),
  );

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    if (isEmpty.value) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = t('请选择集群');
      return info;
    }

    const checkValue = props.disableDialogSubmitMethod
      ? props.disableDialogSubmitMethod(selectedClusterList.value)
      : false;
    if (checkValue) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = _.isString(checkValue) ? checkValue : t('无法保存');
    }
    return info;
  });

  watch(
    () => props.clusterTypes,
    (types) => {
      if (types) {
        activePanelObj.value = clusterTabListMap.value[types[0]];
        [activeTab.value] = types;
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  watch(isShow, () => {
    if (isShow.value && tabList.value) {
      selectedMap.value = tabList.value
        .map((item) => item.id)
        .reduce((result, tabKey) => {
          if (!props.selected[tabKey]) {
            return result;
          }
          const tabSelectMap = {
            map: props.selected[tabKey].reduce(
              (selectResult, selectItem) => ({
                ...selectResult,
                [selectItem.id]: selectItem,
              }),
              {} as Record<string, T>,
            ),
            list: props.selected[tabKey],
          };
          return {
            ...result,
            [tabKey]: tabSelectMap,
          };
        }, {} as SelectMapValueType<T>);

      showTabTips.value = true;
    }
  });

  const initSelectedMap = () => {
    selectedMap.value = Object.keys(selectedMap.value).reduce<SelectMapValueType<T>>((results, id) => {
      Object.assign(results, {
        [id]: {
          map: {},
          list: [],
        },
      });
      return results;
    }, {});
  };

  /**
   * 切换 tab
   */
  const handleChangeTab = (obj: TabItem) => {
    if (activeTab.value === obj.id) {
      return;
    }
    const currentTab = tabList.value.find((item) => item.id === obj.id);
    activeTab.value = obj.id;
    if (currentTab) {
      activePanelObj.value = currentTab;
    }
    if (props.onlyOneType) {
      initSelectedMap();
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
    initSelectedMap();
    isSelectedAll.value = false;
  };

  /**
   * 复制集群域名
   */
  const handleCopyCluster = () => {
    const copyValues = Object.values(selectedMap.value).reduce((result, selectItem) => {
      result.push(...selectItem.list.map((item) => item.master_domain));
      return result;
    }, [] as string[]);

    if (copyValues.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }
    execCopy(copyValues.join('\n'), t('复制成功，共n条', { n: copyValues.length }));
  };

  const handleConfirm = () => {
    const result = Object.keys(selectedMap.value).reduce(
      (result, tabKey) => ({
        ...result,
        [tabKey]: selectedMap.value[tabKey].list,
      }),
      {},
    );
    emits('change', result);
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };

  /**
   * 选择当行数据
   */
  const handleDeleteItem = (data: T, tabKey: string) => {
    delete selectedMap.value[tabKey].map[data.id];
    selectedMap.value[tabKey].list = selectedMap.value[tabKey].list.filter((item) => item.id !== data.id);
  };

  const handleSelectTable = (selected: T[]) => {
    // 如果只允许选一种集群类型, 则清空非当前集群类型的选中列表
    if (props.onlyOneType && selected.length > 0) {
      // 只会有一个key
      Object.keys(selectedMap.value).forEach((key) => {
        if (key !== activeTab.value) {
          selectedMap.value[key] = {
            map: {},
            list: [],
          };
        }
      });
    }
    selectedMap.value[activeTab.value].list = selected;
  };
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .cluster-selector-dialog {
    font-size: @font-size-mini;

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .cluster-selector-tabs {
      height: 42px;
      font-size: @font-size-mini;
      line-height: 42px;
      background-color: #fafbfd;
      border-bottom: 1px solid @border-disable;
      .flex-center();

      .tabs-item {
        min-width: 200px;
        margin-bottom: -1px;
        text-align: center;
        cursor: pointer;
        border: 1px solid @border-disable;
        border-top: 0;
        border-left: 0;
        border-bottom-color: transparent;
      }

      .tabs-item-active {
        background-color: @bg-white;
        border-bottom-color: @border-white;
      }
    }

    .cluster-selector-content {
      height: 580px;
      padding: 16px 24px 0;

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }
    }

    .cluster-selector-result {
      height: 100%;
      padding: 12px 24px;
      font-size: @font-size-mini;
      background-color: #f5f6fa;

      .result-title {
        padding-bottom: 16px;
        .flex-center();

        > span {
          flex: 1;
          font-size: @font-size-normal;
          color: @title-color;
        }

        .result-dropdown {
          font-size: 0;
          line-height: 20px;
        }

        .result-trigger {
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
    }

    .cluster-selector-button {
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
