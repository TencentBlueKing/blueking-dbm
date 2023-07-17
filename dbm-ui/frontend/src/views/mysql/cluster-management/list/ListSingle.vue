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
  <div class="cluster-list">
    <div
      class="cluster-list__operations"
      :class="{'is-flex': isFlexHeader}">
      <DbSearchSelect
        v-model="state.filters"
        class="mb-16"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :placeholder="$t('域名_IP_模块')"
        unique-select
        @change="handleChangeValues" />
      <div class="mb-16">
        <BkButton
          theme="primary"
          @click="handleApply">
          {{ $t('实例申请') }}
        </BkButton>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: $t('请选择集群')
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize(state.selected)">
            {{ $t('批量授权') }}
          </BkButton>
        </span>
        <span
          v-bk-tooltips="{
            disabled: hasData,
            content: $t('请先创建实例')
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasData"
            @click="handleShowExcelAuthorize">
            {{ $t('导入授权') }}
          </BkButton>
        </span>
      </div>
    </div>
    <div
      v-bkloading="{ loading: state.isLoading, zIndex: 2 }"
      class="table-wrapper"
      :class="{'is-shrink-table': !isFullWidth}"
      :style="{ height: tableHeight }">
      <DbOriginalTable
        :key="tableKey"
        :columns="columns"
        :data="state.data"
        :is-anomalies="isAnomalies"
        :is-searching="state.filters.length > 0"
        :pagination="renderPagination"
        remote-pagination
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources(true)"
        @selection-change="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model:is-show="authorizeState.isShow"
    :cluster-type="ClusterTypes.TENDBSINGLE"
    :selected="authorizeState.selected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBSINGLE" />
</template>

<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getResources } from '@services/clusters';
  import { getUseList } from '@services/common';
  import { createTicket } from '@services/ticket';
  import type { ResourceItem } from '@services/types/clusters';
  import type { SearchFilterItem } from '@services/types/common';

  import {
    type IPagination,
    useCopy,
    useDefaultPagination,
    useInfoWithIcon,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    DBTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import DbStatus from '@components/db-status/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';

  import { getMenuListSearch, getSearchSelectorParams, isRecentDays, random } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import ExcelAuthorize from './components/MySQLExcelAuthorize.vue';
  import RenderOperationTag from './components/RenderOperationTag.vue';

  import { getModules } from '@/services/common';
  import type {
    SearchSelectData,
    SearchSelectItem,
    TableSelectionData } from '@/types/bkui-vue';

  type TableProps = InstanceType<typeof Table>['$props'];

  interface ColumnData {
    cell: string,
    data: ResourceItem
  }

  interface State {
    isLoading: boolean,
    pagination: IPagination,
    data: Array<ResourceItem>,
    selected: Array<ResourceItem>,
    filters: Array<any>,
    dbModuleList: Array<SearchFilterItem>,
  }

  interface Props {
    width: number,
    isFullWidth: boolean,
    dragTrigger: (isLeft: boolean) => void
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t, locale } = useI18n();
  const ticketMessage = useTicketMessage();

  const tableKey = ref(random());
  const isCN = computed(() => locale.value === 'zh-cn');
  const isAnomalies = ref(false);
  const isInit = ref(true);
  const state = reactive<State>({
    isLoading: false,
    pagination: useDefaultPagination(),
    data: [],
    selected: [],
    filters: [],
    dbModuleList: [],
  });
  const isFlexHeader = computed(() => props.width >= 460);
  const tableHeight = computed(() => `calc(100% - ${isFlexHeader.value ? 48 : 96}px)`);
  const hasSelected = computed(() => state.selected.length > 0);
  const hasData = computed(() => state.data.length > 0);
  const searchSelectData = computed(() => [{
    name: t('主域名'),
    id: 'domain',
  }, {
    name: 'IP',
    id: 'ip',
  }, {
    name: t('创建人'),
    id: 'creator',
  }, {
    name: t('模块'),
    id: 'db_module_id',
    children: state.dbModuleList,
  }]);

  const tableOperationWidth = computed(() => {
    if (props.isFullWidth) {
      return isCN.value ? 160 : 200;
    }
    return 60;
  });
  const columns = computed<TableProps['columns']>(() => [{
    type: 'selection',
    width: 54,
    label: '',
    fixed: 'left',
  }, {
    label: 'ID',
    field: 'id',
    fixed: 'left',
    width: 100,
  }, {
    label: t('集群名称'),
    field: 'cluster_name',
    minWidth: 200,
    fixed: 'left',
    showOverflowTooltip: false,
    render: ({ data }: ColumnData) => (
      <div class="cluster-name-container">
        <div
          class="cluster-name text-overflow"
          v-overflow-tips>
          <a href="javascript:" onClick={() => handleToDetails(data)}>{data.cluster_name}</a>
        </div>
        <db-icon type="copy" v-bk-tooltips={t('复制集群名称')} onClick={() => copy(data.cluster_name)} />
        <div class="cluster-tags">
          {
            data.operations.map(item => <RenderOperationTag class="cluster-tag" data={item} />)
          }
          {
            data.phase === 'offline'
              ? <db-icon svg type="yijinyong" class="cluster-tag" style="width: 38px; height: 16px;" />
              : null
          }
          {
            isRecentDays(data.create_at, 24 * 3)
              ? <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
              : null
          }
        </div>
      </div>
    ),
  }, {
    label: t('管控区域'),
    field: 'bk_cloud_name',
  }, {
    label: t('状态'),
    field: 'status',
    minWidth: 100,
    render: ({ data }: ColumnData) => {
      const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  }, {
    label: t('主域名'),
    field: 'master_domain',
    minWidth: 200,
    showOverflowTooltip: false,
    render: ({ cell }: ColumnData) => (
      <div class="domain">
        <span class="text-overflow" v-overflow-tips>{cell}</span>
        <i class="db-icon-copy" v-bk-tooltips={t('复制主域名')} onClick={() => copy(cell)} />
      </div>
    ),
  }, {
    label: t('实例'),
    field: 'masters',
    minWidth: 180,
    showOverflowTooltip: false,
    render: ({ data }: ColumnData) => (
      <RenderInstances
        data={data.masters}
        title={t('【inst】实例预览', { inst: data.master_domain })}
        role="master"
        clusterId={data.id}
        clusterType={ClusterTypes.TENDBSINGLE}
      />
    ),
  }, {
    label: t('所属DB模块'),
    field: 'db_module_name',
    width: 140,
    showOverflowTooltip: true,
    render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
  }, {
    label: t('创建人'),
    field: 'creator',
    width: 140,
    render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
  }, {
    label: t('创建时间'),
    field: 'create_at',
    width: 160,
    render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
  }, {
    label: t('操作'),
    field: '',
    width: tableOperationWidth.value,
    fixed: props.isFullWidth ? 'right' : false,
    render: ({ data }: ColumnData) => {
      const getOperations = (theme = 'primary') => {
        const operations = [
          <bk-button
            text
            theme={theme}
            class="mr-8"
            onClick={handleShowAuthorize.bind(null, [data])}>
            { t('授权') }
          </bk-button>,
        ];
        switch (data.phase) {
        case 'online':
          operations.push(<bk-button
            text
            theme={theme}
            class="mr-8"
            onClick={() => handleSwitchCluster(TicketTypes.MYSQL_SINGLE_DISABLE, data)}>
            { t('禁用') }
          </bk-button>);
          break;
        case 'offline':
          operations.push(...[
            <bk-button
              text
              theme={theme}
              class="mr-8"
              onClick={() => handleSwitchCluster(TicketTypes.MYSQL_SINGLE_ENABLE, data)}>
              { t('启用') }
            </bk-button>,
            <bk-button
              text
              theme={theme}
              class="mr-8"
              onClick={() => handleDeleteCluster(data)}>
              { t('删除') }
            </bk-button>,
          ]);
          break;
        }

        return operations;
      };
      if (props.isFullWidth) {
        return getOperations();
      }

      return (
        <bk-dropdown class="operations-more">
          {{
            default: () => <i class="db-icon-more"></i>,
            content: () => (
              <bk-dropdown-menu>
                {
                  getOperations('').map(opt => <bk-dropdown-item>{opt}</bk-dropdown-item>)
                }
              </bk-dropdown-menu>
            ),
          }}
        </bk-dropdown>
      );
    },
  }]);

  watch(() => props.isFullWidth, () => {
    tableKey.value = random();
  });

  // 设置行样式
  const setRowClass = (row: ResourceItem) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === Number(route.query.cluster_id)) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  // 设置用户个人表头信息
  const disabledFields = ['cluster_name', 'master_domain'];
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: disabledFields.includes(item.field as string),
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key) as string[],
    showLineHeight: false,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBSINGLE_TABLE_SETTINGS, defaultSettings);

  const renderPagination = computed(() => {
    if (props.isFullWidth) {
      return { ...state.pagination };
    }
    return {
      ...state.pagination,
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  // 设置轮询
  const { pause, resume } = useTimeoutPoll(() => {
    fetchResources(isInit.value);
  }, 5000, { immediate: false });
  onMounted(() => {
    resume();
  });
  onBeforeUnmount(() => {
    pause();
  });

  async function getMenuList(item: SearchSelectItem | undefined, keyword: string) {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value as SearchSelectData, state.filters);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (state.filters || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      return await fetchUseList(keyword);
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  }

  /**
   * 获取人员列表
   */
  function fetchUseList(fuzzyLookups: string) {
    if (!fuzzyLookups) return [];

    return getUseList({ fuzzy_lookups: fuzzyLookups }).then(res => res.results.map(item => ({
      id: item.username,
      name: item.username,
    })));
  }

  /** 集群授权 */
  const authorizeState = reactive({
    isShow: false,
    selected: [] as ResourceItem[],
  });
  function handleShowAuthorize(selected: ResourceItem[] = []) {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  }
  function handleClearSelected() {
    state.selected = [];
    authorizeState.selected = [];
  }

  // excel 授权
  const isShowExcelAuthorize = ref(false);
  function handleShowExcelAuthorize() {
    isShowExcelAuthorize.value = true;
  }

  /**
   * 获取模块列表
   */
  function fetchModules() {
    return getModules({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: ClusterTypes.TENDBSINGLE,
    }).then((res) => {
      state.dbModuleList = res.map(item => ({
        id: item.db_module_id,
        name: item.name,
      }));
      return state.dbModuleList;
    });
  }
  fetchModules();

  /**
   * 获取列表
   */
  function fetchResources(isLoading = false) {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      type: ClusterTypes.TENDBSINGLE,
      ...state.pagination.getFetchParams(),
      ...getSearchSelectorParams(state.filters),
    };
    isInit.value = false;
    state.isLoading = isLoading;
    return getResources<ResourceItem>(DBTypes.MYSQL, params)
      .then((res) => {
        state.pagination.count = res.count;
        state.data = res.results;
        isAnomalies.value = false;
      })
      .catch(() => {
        state.pagination.count = 0;
        state.data = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleClearSearch() {
    state.filters = [];
    handleChangePage(1);
  }

  /**
   * 查看详情
   */
  function handleToDetails(row: ResourceItem) {
    if (props.isFullWidth) {
      props.dragTrigger(true);
    }
    router.replace({
      query: { cluster_id: row.id },
    });
  }

  /**
   * 表格选中
   */
  function handleTableSelected({ isAll, checked, data, row }: TableSelectionData<ResourceItem>) {
    // 全选 checkbox 切换
    if (isAll) {
      state.selected = checked ? [...data] : [];
      return;
    }

    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = state.selected.findIndex(item => item.id === row.id);
      if (toggleIndex === -1) {
        state.selected.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = state.selected.findIndex(item => item.id === row.id);
    if (toggleIndex > -1) {
      state.selected.splice(toggleIndex, 1);
    }
  }

  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchResources(true);
  }

  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  const handleChangeValues = () => {
    nextTick(() => {
      handleChangePage(1);
    });
  };

  /**
   * 集群启停
   */
  function handleSwitchCluster(type: TicketTypesStrings, data: ResourceItem) {
    if (!type) return;

    const isOpen = type === TicketTypes.MYSQL_SINGLE_ENABLE;
    const title = isOpen ? t('确定启用该集群') : t('确定禁用该集群');
    useInfoWithIcon({
      type: 'warnning',
      title,
      content: () => (
        <div style="word-break: all;">
          {
            isOpen
              ? <p>{t('集群【name】启用后将恢复访问', { name: data.cluster_name })}</p>
              : <p>{t('集群【name】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { name: data.cluster_name })}</p>
          }
        </div>
      ),
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: type,
            details: {
              cluster_ids: [data.id],
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  /**
   * 删除集群
   */
  function handleDeleteCluster(data: ResourceItem) {
    const { cluster_name: name } = data;
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定删除该集群'),
      confirmTxt: t('删除'),
      confirmTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: TicketTypes.MYSQL_SINGLE_DESTROY,
            details: {
              cluster_ids: [data.id],
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  /**
   * 申请实例
   */
  function handleApply() {
    router.push({
      name: 'SelfServiceApplySingle',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  }
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.cluster-list {
  height: 100%;
  padding: 24px 0;
  margin: 0 24px;
  overflow: hidden;

  &__operations {
    &.is-flex {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .bk-search-select {
        order: 2;
        flex: 1;
        max-width: 320px;
        margin-left: 8px;
      }
    }
  }

  .table-wrapper {
    background-color: white;

    .bk-table {
      height: 100%;
    }

    :deep(.bk-table-body) {
      max-height: calc(100% - 100px);
    }
  }

  .is-shrink-table {
    :deep(.bk-table-body) {
      overflow-x: hidden;
      overflow-y: auto;
    }
  }

  :deep(.cell) {
    line-height: normal !important;

    .domain {
      display: flex;
      align-items: center;
    }

    .db-icon-copy {
      display: none;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }

    .operations-more {
      .db-icon-more {
        display: block;
        font-size: @font-size-normal;
        font-weight: bold;
        color: @default-color;
        cursor: pointer;

        &:hover {
          background-color: @bg-disable;
          border-radius: 2px;
        }
      }
    }
  }

  :deep(tr:hover) {
    .db-icon-copy {
      display: inline-block !important;
    }
  }

  :deep(.is-offline) {
    a {
      color: @gray-color;
    }

    .cell {
      color: @disable-color;
    }
  }

  :deep(.cluster-name-container) {
    display: flex;
    align-items: center;
    padding: 8px 0;
    overflow: hidden;

    .cluster-name {
      line-height: 16px;

      &__alias {
        color: @light-gray;
      }
    }

    .cluster-tags {
      display: flex;
      margin-left: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

    .cluster-tag {
      margin: 2px 0;
      flex-shrink: 0;
    }
  }
}
</style>
