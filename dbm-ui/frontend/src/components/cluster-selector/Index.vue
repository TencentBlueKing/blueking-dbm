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
    width="80%"
    @closed="handleClose">
    <BkResizeLayout
      :border="false"
      collapsible
      initial-divide="320px"
      :max="360"
      :min="320"
      placement="right">
      <template #aside>
        <div class="cluster-selector-result">
          <div class="result-title">
            <DbIcon
              class="mr-4"
              type="legend" />
            <span>{{ t('结果预览') }}</span>
            <BkDropdown
              class="result-dropdown"
              :popover-options="{
                clickContentAutoHide: true,
              }"
              trigger="click">
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
          <div class="result-content">
            <Component
              :is="activePanelObj.resultContent"
              :display-key="activePanelObj.previewResultKey"
              :selected-map="selectedMap"
              :show-title="activePanelObj.showPreviewResultTitle"
              :tab-list="tabList"
              @delete="handleDeleteItem" />
          </div>
        </div>
      </template>
      <template #main>
        <div
          ref="clusterTabsRef"
          class="cluster-selector-tabs">
          <BkPopover
            v-for="tabItem of tabList"
            :key="tabItem.id"
            ref="tabTips"
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
            :key="activeTab"
            :active-tab="activeTab"
            :column-status-filter="activePanelObj.columnStatusFilter"
            :custom-colums="activePanelObj.customColums"
            :disabled-row-config="activePanelObj.disabledRowConfig"
            :get-resource-list="activePanelObj.getResourceList"
            :multiple="activePanelObj.multiple"
            :search-select-list="activePanelObj.searchSelectList"
            :selected="selectedMap[activeTab] ?? []"
            @change="handleSelectTable" />
        </div>
      </template>
    </BkResizeLayout>
    <template #footer>
      <span class="mr-24">
        <slot
          v-if="slots.submitTips"
          :cluster-list="selectedClusterList"
          name="submitTips" />
      </span>
      <span v-bk-tooltips="submitButtonDisabledInfo.tooltips">
        <BkButton
          v-test="{ type: 'button', value: 'clusterSelectorConfirm' }"
          class="w-88"
          :disabled="submitButtonDisabledInfo.disabled"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml-8 w-88"
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
      | OracleHaModel
      | OracleSingleModel
  ">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { ref, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import OracleHaModel from '@services/model/oracle/oracle-ha';
  import OracleSingleModel from '@services/model/oracle/oracle-single';
  import RedisModel from '@services/model/redis/redis';
  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getMongoList } from '@services/source/mongodb';
  import { getOracleHaClusterList } from '@services/source/oracleHaCluster';
  import { getOracleSingleClusterList } from '@services/source/oracleSingleCluster';
  import { getRedisList } from '@services/source/redis';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';
  import { getSingleClusterList } from '@services/source/sqlserverSingleCluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';
  import { getTendbsingleList } from '@services/source/tendbsingle';
  import type { ListBase } from '@services/types';

  import { ClusterTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  import ClusterTable from './components/ClusterTable.vue';
  import ResultPreview from './components/result-preview/Index.vue';
  import { getTabRowKey } from './components/tableConfig';

  export type TabListType = {
    // 状态列
    columnStatusFilter?: (data: any) => boolean;
    // 自定义列
    customColums?: any[];
    // 不可选行及提示
    disabledRowConfig?: {
      handler: (data: any) => boolean;
      tip: string;
    }[];
    // 查询接口
    getResourceList?: (params: any) => Promise<ListBase<Record<string, any>[]>>;
    id: string;
    // 多选模式
    multiple?: boolean;
    name: string;
    // 结果预览使用的key
    previewResultKey?: string;
    resultContent: any;
    // 搜索栏下拉选项
    searchSelectList?: QuickSearchProps['data'];
    showPreviewResultTitle?: boolean;
    tableContent: any;
  }[];

  export type TabItem = TabListType[number];

  export type TabConfig = Omit<TabItem, 'tableContent' | 'resultContent'>;

  // 按 tab id 索引的选中结果，与 Props['selected'] 同构
  export type SelectMapValueType<T> = Record<string, T[]>;

  export interface Props<T> {
    clusterTypes: string[];
    disableDialogSubmitMethod?: (hostList: Array<string>) => string | boolean;
    onlyOneType?: boolean;
    selected: Record<string, T[]>;
    supportOfflineData?: boolean;
    tabListConfig?: Record<string, TabConfig>;
  }

  export type Emits<T> = (e: 'change', value: Props<T>['selected']) => void;

  const props = defineProps<Props<T>>();

  const emits = defineEmits<Emits<T>>();

  const slots = defineSlots<{
    submitTips?: (params: { clusterList: string[] }) => VNode;
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  // 13 个 tab 的禁用规则、选择模式、表格与结果预览组件完全一致，只有查询接口与名称不同
  const createTabItem = (config: Pick<TabItem, 'getResourceList' | 'id' | 'name' | 'showPreviewResultTitle'>) => ({
    disabledRowConfig: [
      {
        handler: (data: T) => data.isOffline,
        tip: t('集群已禁用'),
      },
    ],
    multiple: true,
    resultContent: ResultPreview,
    tableContent: ClusterTable,
    ...config,
  });

  const tabListMap: Record<string, TabItem> = {
    [ClusterTypes.MONGO_REPLICA_SET]: createTabItem({
      // 副本集与分片集群共用 getMongoList，须带上 cluster_type 区分
      getResourceList: (params: ServiceParameters<typeof getMongoList>) =>
        getMongoList({
          cluster_type: ClusterTypes.MONGO_REPLICA_SET,
          ...params,
        }),
      id: ClusterTypes.MONGO_REPLICA_SET,
      name: t('副本集'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.MONGO_SHARED_CLUSTER]: createTabItem({
      getResourceList: (params: ServiceParameters<typeof getMongoList>) =>
        getMongoList({
          cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
          ...params,
        }),
      id: ClusterTypes.MONGO_SHARED_CLUSTER,
      name: t('分片集群'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.ORACLE_PRIMARY_STANDBY]: createTabItem({
      getResourceList: getOracleHaClusterList,
      id: ClusterTypes.ORACLE_PRIMARY_STANDBY,
      name: t('Oracle 主从'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.ORACLE_SINGLE_NONE]: createTabItem({
      getResourceList: getOracleSingleClusterList,
      id: ClusterTypes.ORACLE_SINGLE_NONE,
      name: t('Oracle 单节点'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.REDIS]: createTabItem({
      getResourceList: getRedisList,
      id: ClusterTypes.REDIS,
      name: t('集群选择'),
    }),
    [ClusterTypes.REDIS_INSTANCE]: createTabItem({
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: ClusterTypes.REDIS_INSTANCE,
          ...params,
        }),
      id: ClusterTypes.REDIS_INSTANCE,
      name: t('Redis 主从'),
    }),
    [ClusterTypes.SQLSERVER_HA]: createTabItem({
      getResourceList: getHaClusterList,
      id: ClusterTypes.SQLSERVER_HA,
      name: t('SqlServer 主从'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.SQLSERVER_SINGLE]: createTabItem({
      getResourceList: getSingleClusterList,
      id: ClusterTypes.SQLSERVER_SINGLE,
      name: t('SqlServer 单节点'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.TENDBCLUSTER]: createTabItem({
      getResourceList: getTendbClusterList,
      id: ClusterTypes.TENDBCLUSTER,
      name: t('集群选择'),
    }),
    [ClusterTypes.TENDBHA]: createTabItem({
      getResourceList: getTendbhaList,
      id: ClusterTypes.TENDBHA,
      name: t('主从集群'),
      showPreviewResultTitle: true,
    }),
    [ClusterTypes.TENDBSINGLE]: createTabItem({
      getResourceList: getTendbsingleList,
      id: ClusterTypes.TENDBSINGLE,
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    }),
    tendbclusterSlave: createTabItem({
      getResourceList: getTendbClusterList,
      id: 'tendbclusterSlave',
      name: t('集群选择'),
    }),
    tendbhaSlave: createTabItem({
      getResourceList: getTendbhaSalveList,
      id: 'tendbhaSlave',
      name: t('主从集群'),
    }),
  };

  // v-for 上的 ref，拿到的是 BkPopover 实例数组
  const tabTipsRef = useTemplateRef<{ hide: () => void }[]>('tabTips');
  const activeTab = ref(ClusterTypes.TENDBCLUSTER as string);
  const selectedMap = ref<SelectMapValueType<T>>({});

  const clusterTabListMap = computed<Record<string, TabItem>>(() => {
    if (!props.tabListConfig) {
      return tabListMap;
    }
    return Object.entries(props.tabListConfig).reduce<Record<string, TabItem>>(
      (results, [type, config]) => {
        if (!config) {
          return results;
        }
        const disabledRowConfigList = props.supportOfflineData
          ? []
          : [
              {
                handler: (data: T) => data.isOffline,
                tip: t('集群已禁用'),
              },
            ];
        if (config.disabledRowConfig) {
          // 外部设置了 disabledRowConfig, 需要追加到 disabledRowConfig列表
          disabledRowConfigList.push(...config.disabledRowConfig);
        }
        return Object.assign(results, {
          [type]: {
            ...results[type],
            ...config,
            disabledRowConfig: disabledRowConfigList,
          },
        });
      },
      { ...tabListMap },
    );
  });

  const tabList = computed(() =>
    props.clusterTypes ? props.clusterTypes.map((type) => clusterTabListMap.value[type]) : [],
  );

  const activePanelObj = computed(() => clusterTabListMap.value[activeTab.value]);

  // 所有 tab 都没有选中项
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), (clusterList) => clusterList.length < 1));

  const selectedClusterList = computed(() =>
    Object.values(selectedMap.value).flatMap((clusterList) => clusterList.map((item) => item.master_domain)),
  );

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
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
        [activeTab.value] = types;
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(isShow, () => {
    if (isShow.value && tabList.value) {
      selectedMap.value = tabList.value.reduce<SelectMapValueType<T>>((result, tabItem) => {
        if (!props.selected[tabItem.id]) {
          return result;
        }
        return Object.assign(result, {
          [tabItem.id]: _.cloneDeep(props.selected[tabItem.id]),
        });
      }, {});
    }
  });

  const initSelectedMap = () => {
    selectedMap.value = Object.keys(selectedMap.value).reduce<SelectMapValueType<T>>(
      (results, id) => Object.assign(results, { [id]: [] }),
      {},
    );
  };

  /**
   * 切换 tab
   */
  const handleChangeTab = (obj: TabItem) => {
    if (activeTab.value === obj.id) {
      return;
    }
    activeTab.value = obj.id;
    if (props.onlyOneType) {
      initSelectedMap();
    }
  };

  /**
   * 关闭提示
   */
  const handleCloseTabTips = () => {
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
  };

  /**
   * 复制集群域名
   */
  const handleCopyCluster = () => {
    const copyValues = selectedClusterList.value;
    if (copyValues.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }
    execCopy(copyValues.join('\n'), t('复制成功，共n条', { n: copyValues.length }));
  };

  const handleConfirm = () => {
    emits('change', { ...selectedMap.value });
    handleClose();
  };

  const handleClose = () => {
    isShow.value = false;
  };

  /**
   * 选择当行数据
   */
  const handleDeleteItem = (data: T, tabKey: string) => {
    // 按该 tab 的行标识删除：tendbhaSlave 等一个集群 id 拆多行的 tab，用 id 会把同组的其它行一起删掉
    const rowKey = getTabRowKey(tabKey);
    const targetKey = _.get(data, rowKey);
    selectedMap.value[tabKey] = selectedMap.value[tabKey].filter((item) => _.get(item, rowKey) !== targetKey);
  };

  const handleSelectTable = (selected: T[]) => {
    // 如果只允许选一种集群类型, 则清空非当前集群类型的选中列表
    if (props.onlyOneType && selected.length > 0) {
      // 只会有一个key
      Object.keys(selectedMap.value).forEach((key) => {
        if (key !== activeTab.value) {
          selectedMap.value[key] = [];
        }
      });
    }
    selectedMap.value[activeTab.value] = selected;
  };
</script>

<style lang="less">
  .cluster-selector-dialog {
    display: block;
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;

    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .cluster-selector-tabs {
      display: flex;

      .tabs-item {
        display: flex;
        height: 40px;
        cursor: pointer;
        background-color: #fafbfd;
        border-bottom: 1px solid #dcdee5;
        justify-content: center;
        align-items: center;
        flex: 1;

        & ~ .tabs-item {
          border-left: 1px solid #dcdee5;
        }
      }

      .tabs-item-active {
        background-color: #fff;
        border-bottom-color: transparent;
      }
    }

    .cluster-selector-content {
      height: 570px;
      padding: 0 24px;

      :deep(.bk-pagination-small-list) {
        order: 3;
        flex: 1;
        justify-content: flex-end;
      }
    }

    .cluster-selector-result {
      height: 100%;
      font-size: @font-size-mini;
      background-color: #f5f6fa;

      .result-title {
        display: flex;
        height: 40px;
        padding: 12px 24px;
        font-weight: bold;
        background-color: #fff;
        align-items: center;

        > span {
          flex: 1;
          font-size: 12px;
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

      .result-content {
        padding: 12px 24px;
      }
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
