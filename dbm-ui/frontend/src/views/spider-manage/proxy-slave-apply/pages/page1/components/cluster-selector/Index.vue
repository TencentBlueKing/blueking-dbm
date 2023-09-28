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
              v-for="(tabSelected, tabKey) in selectedMap"
              :key="tabKey">
              <CollapseMini
                v-if="Object.keys(tabSelected).length > 0"
                collapse
                :count="Object.keys(tabSelected).length"
                :title="getTabInfo(tabKey)?.name">
                <div
                  v-for="clusterItem in tabSelected"
                  :key="clusterItem.id"
                  class="result__item">
                  <span
                    v-overflow-tips
                    class="text-overflow">{{ clusterItem.master_domain }}</span>
                  <i
                    class="db-icon-close result__remove"
                    @click="handleSelecteRow(clusterItem, false)" />
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
              v-for="tabItem of tabList"
              :key="tabItem.id"
              ref="tabTipsRef"
              :disabled="!showSwitchTabTips"
              theme="light">
              <div
                class="tabs__item"
                :class="[{ 'tabs__item--active': tabItem.id === activeTab }]"
                @click.stop="handleChangeTab(tabItem.id)">
                {{ tabItem.name }}
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
            <DbSearchSelect
              v-model="searchSelectValue"
              class="mb-16"
              :data="searchSelectData"
              :placeholder="$t('域名_模块')"
              unique-select
              @change="handleSearch" />
            <BkLoading
              :loading="isLoading"
              :z-index="2">
              <DbOriginalTable
                class="table-box"
                :columns="columns"
                :data="tableData"
                :height="500"
                :is-anomalies="isAnomalies"
                :is-searching="searchSelectValue.length > 0"
                :pagination="pagination"
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
<script setup lang="tsx" generic="T extends SpiderModel">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useFormItem } from 'bkui-vue/lib/shared';
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SpiderModel from '@services/model/spider/spider';
  import type { ResourceItem } from '@services/types/clusters';
  import type { ListBase } from '@services/types/common';

  import { useCopy } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterRelatedTasks from '@components/cluster-selector/cluster-relate-tasks/Index.vue';
  import CollapseMini from '@components/cluster-selector/CollapseMini.vue';
  import { useClusterData } from '@components/cluster-selector/useSpiderClusterData';
  import DbStatus from '@components/db-status/index.vue';

  import {
    getSearchSelectorParams,
    makeMap,
    messageWarn,
  } from '@utils';

  interface Props {
    isShow: boolean;
    selected: Record<string, T[]>,
    onlyOneType?: boolean;
    tabList: {name: string; id: string}[],
    // eslint-disable-next-line vue/no-unused-properties
    getResourceList: (params: Record<string, any>) => Promise<ListBase<T[]>>
  }

  interface Emits {
    (e: 'update:is-show', value: boolean): void,
    (e: 'change', value: Props['selected']): void,
  }

  type ValueOf<T> = T[keyof T]

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    selected: () =>  ({}),
    onlyOneType: false,
    tabList: () => [
      {
        name: '高可用集群',
        id: ClusterTypes.TENDBHA,
      },
      {
        name: '单节点集群',
        id: ClusterTypes.TENDBSINGLE,
      },
    ],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const checkSelectedAll = () => {
    if (!selectedMap.value[activeTab.value]
      || Object.keys(selectedMap.value[activeTab.value]).length < 1) {
      isSelectedAll.value = false;
      return;
    }

    for (let i = 0; i < tableData.value.length; i++) {
      if (!selectedMap.value[activeTab.value][tableData.value[i].id]) {
        isSelectedAll.value = false;
      }
    }
  };

  const formItem = useFormItem();

  const tabTipsRef = ref();
  const activeTab = ref(props.tabList[0].id);
  const showTabTips = ref(false);
  const searchSelectValue = ref<ISearchValue[]>([]);
  const selectedMap = shallowRef<Record<string, Record<string, ValueOf<Props['selected']>[0]>>>({});
  const isSelectedAll = ref(false);

  const {
    isLoading,
    pagination,
    isAnomalies,
    dbModuleList,
    data: tableData,
    fetchModules,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useClusterData<ValueOf<Props['selected']>[0]>(activeTab, searchSelectValue);

  // 显示切换 tab tips
  const showSwitchTabTips = computed(() => showTabTips.value && props.onlyOneType);
  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), item => Object.keys(item).length < 1));

  const searchSelectData = computed(() => [{
    name: t('主访问入口'),
    id: 'domain',
  }, {
    name: t('模块'),
    id: 'db_module_id',
    children: dbModuleList.value,
  }]);
  // 选中域名列表
  const selectedDomainMap = computed(() => Object.values(selectedMap.value)
    .reduce((result, selectItem) => {
      const masterDomainMap  = makeMap(Object.keys(selectItem));
      return Object.assign({}, result, masterDomainMap);
    }, {} as Record<string, boolean>));

  const columns = [
    {
      width: 60,
      label: () => (
      <bk-checkbox
        key={`${pagination.current}_${activeTab.value}`}
        model-value={isSelectedAll.value}
        label={true}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={handleSelecteAll}
      />
    ),
      render: ({ data }: { data: ValueOf<Props['selected']>[0] }) => {
        if (data.spider_slave.length > 0) {
          return (
            <bk-popover theme="dark" placement="top">
              {{
                default: () => <bk-checkbox style="vertical-align: middle;" disabled />,
                content: () => <span>{t('该集群已有只读集群')}</span>,
              }}
          </bk-popover>
          );
        }
        return (
      <bk-checkbox
        style="vertical-align: middle;"
        model-value={Boolean(selectedDomainMap.value[data.id])}
        label={true}
        onClick={(e: Event) => e.stopPropagation()}
        onChange={(value: boolean) => handleSelecteRow(data, value)}
      />
        );
      },
    },
    {
      label: t('集群'),
      field: 'cluster_name',
      showOverflowTooltip: true,
      render: ({ data }: { data: ResourceItem }) => (
      <div class="cluster-name-box">
          <div class="cluster-name">{data.master_domain}</div>
          {data.operations && data.operations.length > 0 && <bk-popover
            theme="light"
            width="360">
            {{
              default: () => <bk-tag theme="info" class="tag-box">{data.operations.length}</bk-tag>,
              content: () => <ClusterRelatedTasks data={data.operations} />,
            }}
          </bk-popover>}
      </div>),
    },
    {
      label: t('域名'),
      field: 'master_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      showOverflowTooltip: true,
    },
    {
      label: t('所属模块'),
      field: 'db_module_name',
      showOverflowTooltip: true,
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 100,
      render: ({ data }: { data: ResourceItem }) => {
        const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
  ];

  watch(() => props.isShow, (show) => {
    if (show) {
      selectedMap.value = props.tabList.map(({ id }) => id).reduce((result, tabKey) => {
        if (!props.selected[tabKey]) {
          return result;
        }
        const tabSelectMap = props.selected[tabKey].reduce((selectResult, selectItem) => ({
          ...selectResult,
          [selectItem.id]: selectItem,
        }), {} as Record<string, ValueOf<Props['selected']>[0]>);
        return {
          ...result,
          [tabKey]: tabSelectMap,
        };
      }, {} as Record<string, Record<string, ValueOf<Props['selected']>[0]>>);
      showTabTips.value = true;
      fetchModules();
      handleTablePageChange(1);
    }
  });

  watch(() => activeTab.value, () => {
    searchSelectValue.value = [];
    fetchModules();
    handleTablePageChange(1);
  });

  // 获取 tab 信息
  const getTabInfo = (key: string) => props.tabList.find(tab => tab.id === key);

  /**
   * 切换 tab
   */
  const handleChangeTab = (id: string) => {
    if (activeTab.value === id) return;

    activeTab.value = id;
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
   * 清空过滤列表
   */
  const handleClearSearch = () => {
    searchSelectValue.value = [];
    nextTick(() => {
      handleTablePageChange(1);
    });
  };

  /**
   * 过滤列表
   */
  const handleSearch = () => {
    nextTick(() => {
      handleTablePageChange(1);
    });
  };

  /**
   * 全选当页数据
   */
  const handleSelecteAll = (value: boolean) => {
    for (const data of tableData.value) {
      if (data.spider_slave.length === 0) {
        handleSelecteRow(data, value);
      }
    }
  };

  /**
   * 选择当行数据
   */
  const handleSelecteRow = (data: ValueOf<Props['selected']>[0], value: boolean) => {
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

    checkSelectedAll();
  };

  const handleRowClick = (row:any, data: ValueOf<Props['selected']>[0]) => {
    if (data.spider_slave.length > 0) {
      return;
    }
    const selectedMapMemo = { ...selectedMap.value };
    if (!selectedMapMemo[activeTab.value]) {
      selectedMapMemo[activeTab.value] = {};
    }
    if (selectedMapMemo[activeTab.value][data.id]) {
      delete selectedMapMemo[activeTab.value][data.id];
    } else {
      selectedMapMemo[activeTab.value][data.id] = data;
    }
    selectedMap.value = selectedMapMemo;
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

  function handleCopyCluster() {
    const copyValues = Object.values(selectedMap.value).reduce((result, selectItem) => {
      result.push(...Object.values(selectItem).map(item => item.master_domain));
      return result;
    }, [] as string[]);

    if (copyValues.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }

    copy(copyValues.join('\n'));
  }

  function handleConfirm() {
    const result = Object.keys(selectedMap.value).reduce((result, tabKey) => ({
      ...result,
      [tabKey]: Object.values(selectedMap.value[tabKey]),
    }), {});
    emits('change', result);
    nextTick(() => {
      formItem?.validate?.('change');
      formItem?.validate?.('blur');
    });
    handleClose();
  }

  function handleClose() {
    emits('update:is-show', false);
  }

  function handleTablePageChange(value: number) {
    handleChangePage(value)
      .then(() => {
        checkSelectedAll();
      });
  }

  function handleTableLimitChange(value: number) {
    handeChangeLimit(value)
      .then(() => {
        checkSelectedAll();
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

      .table-box {
        :deep(.cluster-name-box) {
          display: flex;
          width: 100%;
          align-items: center;
          overflow: hidden;

          .cluster-name {
            margin-right: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex:1;
          }

          .tag-box {
            height: 16px;
            color: #3A84FF;
            border-radius: 8px !important;
          }
        }
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
./useSpiderClusterData
