<template>
  <div class="sqlserver-ha-cluster-list-page">
    <div class="header-action">
      <BkButton
        v-db-console="'sqlserver.haClusterList.instanceApply'"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </BkButton>
      <ClusterBatchOperation
        v-db-console="'sqlserver.haClusterList.batchOperation'"
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        :selected="selected"
        @success="fetchData" />
      <BkButton
        v-db-console="'sqlserver.haClusterList.importAuthorize'"
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
      <TagSearch @search="handleTagSearch" />
      <DbSearchSelect
        class="header-select"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <ClusterTable
      ref="tableRef"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.SQLSERVER_HA"
      :data-source="getHaClusterList"
      :settings="settings"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.SQLSERVER_HA">
          <template #default="{ data }">
            <div v-db-console="'sqlserver.haClusterList.authorize'">
              <BkButton
                :disabled="data.isOffline"
                text
                @click="handleShowAuthorize([data])">
                {{ t('授权') }}
              </BkButton>
            </div>
            <div v-db-console="'sqlserver.haClusterList.enable'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isStarting || !data.isOffline"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'sqlserver.haClusterList.reset'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="Boolean(data.operationTicketId)"
                  text
                  @click="handleResetCluster(data)">
                  {{ t('重置') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'sqlserver.haClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isOffline || Boolean(data.operationTicketId)"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'sqlserver.haClusterList.delete'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <ClusterDomainDnsRelation :data="data" />
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('主访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
      </template>
      <template #slaveDomain>
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Master"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          field="slaves"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Slave"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
      </template>
      <template #syncMode>
        <BkTableColumn
          field="sync_mode"
          :label="t('同步模式')"
          :width="120">
          <template #default="{data}: {data: SqlServerHaModel}">
            {{ data.sync_mode || '--' }}
          </template>
        </BkTableColumn>
      </template>
      <template #moduleNames>
        <ModuleNameColumn :cluster-type="ClusterTypes.SQLSERVER_HA" />
      </template>
    </ClusterTable>
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
    :data="currentData" />

  <TableDetailDialog
    v-model="isShowDetail"
    :default-offset-left="300"
    @close="handleDetailClose">
    <ClusterDetail
      v-if="clusterId"
      :cluster-id="clusterId" />
  </TableDetailDialog>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    ModuleNameColumn,
    OperationColumn,
    RoleColumn,
    SlaveDomainColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/sqlserver/common/ha-cluster-detail/Index.vue';
  import ClusterReset from '@views/db-manage/sqlserver/components/cluster-reset/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const router = useRouter();
  const route = useRoute();

  const { t } = useI18n();

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.SQLSERVER,
    {
      onSuccess: () => fetchData(),
    },
  );

  const {
    batchSearchIpInatanceList,
    clearSearchValue,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    isFilter,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(),
    searchType: ClusterTypes.SQLSERVER_HA,
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('SqlServerHaClusterDetail');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false);
  const currentData = ref<SqlServerHaModel>();
  const selected = ref<SqlServerHaModel[]>([]);
  const tagSearchValue = ref<Record<string, any>>({});

  /** 集群授权 */
  const authorizeShow = ref(false);
  const authorizeSelected = ref<
    {
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name: string;
      master_domain: string;
    }[]
  >([]);

  const getTableInstance = () => tableRef.value;

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const searchSelectData = computed(() => [
    {
      async: false,
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      async: false,
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'cluster_ids',
      multiple: true,
      name: 'ID',
    },
    {
      async: false,
      id: 'name',
      multiple: true,
      name: t('集群名称'),
    },
    {
      children: searchAttrs.value.bk_cloud_id,
      id: 'bk_cloud_id',
      multiple: true,
      name: t('管控区域'),
    },
    {
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
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.db_module_id,
      id: 'db_module_id',
      multiple: true,
      name: t('所属DB模块'),
    },
    {
      children: searchAttrs.value.major_version,
      id: 'major_version',
      multiple: true,
      name: t('版本'),
    },
    {
      children: searchAttrs.value.region,
      id: 'region',
      multiple: true,
      name: t('地域'),
    },
    {
      id: 'creator',
      name: t('创建人'),
    },
    {
      children: searchAttrs.value.time_zone,
      id: 'time_zone',
      multiple: true,
      name: t('时区'),
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
      'tag',
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

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchData();
  };

  const fetchData = () => {
    tableRef.value!.fetchData({ ...getSearchSelectorParams(searchValue.value), ...tagSearchValue.value, ...sortValue });
  };

  const handleResetCluster = (data: SqlServerHaModel) => {
    currentData.value = data;
    isShowClusterReset.value = true;
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
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
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: String(route.name),
      },
    });
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
      margin-bottom: 16px;
      gap: 8px;

      .tag-search-main {
        margin-left: auto;
      }

      .header-select {
        flex: 1;
        max-width: 500px;
      }
    }
  }
</style>
