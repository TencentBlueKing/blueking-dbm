<template>
  <div class="sqlserver-ha-cluster-list-page">
    <div class="header-action">
      <div class="mb-16">
        <BkButton
          v-db-console="'sqlserver.haClusterList.instanceApply'"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </BkButton>
        <ClusterBatchOperation
          v-db-console="'sqlserver.haClusterList.batchOperation'"
          class="ml-8"
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          :selected="selected"
          @success="handleBatchOperationSuccess" />
        <BkButton
          v-db-console="'sqlserver.haClusterList.importAuthorize'"
          class="ml-8"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
        <DropdownExportExcel
          v-db-console="'sqlserver.haClusterList.export'"
          export-type="cluster"
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="sqlserver_ha" />
        <ClusterIpCopy
          v-db-console="'sqlserver.haClusterList.batchCopy'"
          :selected="selected" />
      </div>
      <DbSearchSelect
        class="header-select mb-16"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getHaClusterList"
      releate-url-query
      :row-class="setRowClass"
      :row-config="{
        useKey: true,
        keyField: 'id',
      }"
      :scroll-y="{ enabled: true, gt: 0 }"
      selectable
      :settings="settings"
      :show-overflow="false"
      show-settings
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <IdColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      <MasterDomainColumn
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        field="master_domain"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('主访问入口')"
        :selected-list="selected"
        @go-detail="handleToDetails"
        @refresh="fetchData" />
      <ClusterNameColumn
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :selected-list="selected"
        @refresh="fetchData" />
      <SlaveDomainColumn
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :selected-list="selected" />
      <StatusColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      <ClusterStatsColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      <RoleColumn
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        field="masters"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        label="Master"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <RoleColumn
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        field="slaves"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        label="Slave"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <BkTableColumn
        field="sync_mode"
        :label="t('同步模式')"
        :width="120">
        <template #default="{data}: {data: SqlServerHaModel}">
          {{ data.sync_mode || '--' }}
        </template>
      </BkTableColumn>
      <ModuleNameColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      <CommonColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      <BkTableColumn
        :fixed="isStretchLayoutOpen ? false : 'right'"
        :label="t('操作')"
        :min-width="160"
        :show-overflow="false">
        <template #default="{data}: {data: SqlServerHaModel}">
          <BkButton
            v-db-console="'sqlserver.haClusterList.authorize'"
            class="mr-8"
            :disabled="data.isOffline"
            text
            theme="primary"
            @click="handleShowAuthorize([data])">
            {{ t('授权') }}
          </BkButton>
          <OperationBtnStatusTips
            v-db-console="'sqlserver.haClusterList.enable'"
            :data="data">
            <BkButton
              class="mr-8"
              :disabled="data.isStarting || !data.isOffline"
              text
              theme="primary"
              @click="handleEnableCluster([data])">
              {{ t('启用') }}
            </BkButton>
          </OperationBtnStatusTips>
          <OperationBtnStatusTips
            v-db-console="'sqlserver.haClusterList.reset'"
            :data="data">
            <BkButton
              class="mr-8"
              :disabled="Boolean(data.operationTicketId)"
              text
              theme="primary"
              @click="handleResetCluster(data)">
              {{ t('重置') }}
            </BkButton>
          </OperationBtnStatusTips>
          <MoreActionExtend>
            <BkDropdownItem v-db-console="'sqlserver.haClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isOffline || Boolean(data.operationTicketId)"
                  text
                  theme="primary"
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </BkButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
            <BkDropdownItem v-db-console="'sqlserver.haClusterList.delete'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  text
                  theme="primary"
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </BkButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
          </MoreActionExtend>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_HA"
    :ticket-type="TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES" />
  <ClusterReset
    v-if="currentData"
    v-model:is-show="isShowClusterReset"
    :data="currentData"></ClusterReset>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterNameColumn from '@views/db-manage/common/cluster-table-column/ClusterNameColumn.vue';
  import ClusterStatsColumn from '@views/db-manage/common/cluster-table-column/ClusterStatsColumn.vue';
  import CommonColumn from '@views/db-manage/common/cluster-table-column/CommonColumn.vue';
  import IdColumn from '@views/db-manage/common/cluster-table-column/IdColumn.vue';
  import MasterDomainColumn from '@views/db-manage/common/cluster-table-column/MasterDomainColumn.vue';
  import ModuleNameColumn from '@views/db-manage/common/cluster-table-column/ModuleNameColumn.vue';
  import RoleColumn from '@views/db-manage/common/cluster-table-column/RoleColumn.vue';
  import SlaveDomainColumn from '@views/db-manage/common/cluster-table-column/SlaveDomainColumn.vue';
  import StatusColumn from '@views/db-manage/common/cluster-table-column/StatusColumn.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterReset from '@views/db-manage/sqlserver/components/cluster-reset/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const haClusterData = defineModel<{
    clusterId: number;
  }>('haClusterData');

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();

  const { t } = useI18n();

  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.SQLSERVER,
    {
      onSuccess: () => fetchData(),
    },
  );

  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const {
    searchAttrs,
    searchValue,
    sortValue,
    batchSearchIpInatanceList,
    isFilter,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.SQLSERVER_HA,
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false);
  const currentData = ref<SqlServerHaModel>();
  const selected = ref<SqlServerHaModel[]>([]);

  /** 集群授权 */
  const authorizeShow = ref(false);
  const authorizeSelected = ref<
    {
      master_domain: string;
      cluster_name: string;
      db_module_name: string;
      cluster_type: ClusterTypes;
    }[]
  >([]);

  const getTableInstance = () => tableRef.value;

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const searchSelectData = computed(() => [
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
      async: false,
    },
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
      multiple: true,
      async: false,
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
      multiple: true,
      async: false,
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
    },
    {
      name: t('所属DB模块'),
      id: 'db_module_id',
      multiple: true,
      children: searchAttrs.value.db_module_id,
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.SQLSERVER_HA_TABLE_SETTINGS, {
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      'slave_domain',
      'masters',
      'slaves',
      'db_module_id',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'spec_name',
    ],
    disabled: ['master_domain'],
  });

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then((res) =>
        res.results.map((item) => ({
          id: item.username,
          name: item.username,
        })),
      );
    }

    // 不需要远层加载
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData(
      { ...getSearchSelectorParams(searchValue.value) },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ...sortValue,
      },
      loading,
    );
    isInit = false;
  };

  const handleResetCluster = (data: SqlServerHaModel) => {
    currentData.value = data;
    isShowClusterReset.value = true;
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  // 设置行样式
  const setRowClass = (row: SqlServerHaModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (haClusterData.value && row.id === haClusterData.value.clusterId) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  /**
   * 查看详情
   */
  const handleToDetails = (clusterId: number) => {
    stretchLayoutSplitScreen();
    haClusterData.value = {
      clusterId,
    };
  };

  const handleSelection = (key: unknown, list: SqlServerHaModel[]) => {
    selected.value = list;
  };

  const handleClearSelected = () => {
    selected.value = [];
    authorizeSelected.value = [];
  };

  const handleShowAuthorize = (selected: SqlServerHaModel[]) => {
    authorizeShow.value = true;
    authorizeSelected.value = selected;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceHaApply',
      query: {
        bizId: currentBizId,
        from: String(route.name),
      },
    });
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .sqlserver-ha-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .header-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    tr {
      &.is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      &.is-offline {
        .vxe-cell {
          color: #c4c6cc !important;
        }
      }
    }
  }
</style>
