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
        :selected="selectedList"
        @success="fetchData" />
      <BkButton
        v-db-console="'sqlserver.haClusterList.importAuthorize'"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'sqlserver.haClusterList.export'"
        export-type="cluster"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="sqlserver_ha" />
      <ClusterIpCopy
        v-db-console="'sqlserver.haClusterList.batchCopy'"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.SQLSERVER_HA"
      :data-source="getHaClusterList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.SQLSERVER_HA">
          <template #default="{ data }: { data: SqlServerHaModel }">
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
                  :disabled="!data.isOffline"
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
          :is-filter="isSearching"
          :label="t('主访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
      </template>
      <template #slaveDomain>
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Master"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          field="slaves"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Slave"
          :selected-list="selectedList"
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
    v-model="isShowAuthorize"
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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

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
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterReset from '@views/db-manage/sqlserver/common/cluster-operations/cluster-reset/Index.vue';
  import ClusterDetail from '@views/db-manage/sqlserver/common/ha-cluster-detail/Index.vue';

  const router = useRouter();
  const route = useRoute();

  const { t } = useI18n();

  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.SQLSERVER_HA);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.SQLSERVER,
    {
      onSuccess: () => fetchData(),
    },
  );

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('SqlServerHaClusterDetail');
  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<SqlServerHaModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false);
  const currentData = ref<SqlServerHaModel>();

  /** 集群授权 */
  const isShowAuthorize = ref(false);
  const authorizeSelected = ref<
    {
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name: string;
      master_domain: string;
    }[]
  >([]);

  const getTableInstance = () => tableRef.value;

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.SQLSERVER_HA_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchData = () => {
    tableRef.value!.fetchData(searchValue.value);
  };

  const handleResetCluster = (data: SqlServerHaModel) => {
    currentData.value = data;
    isShowClusterReset.value = true;
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleClearSelected = () => {
    selectedList.value = [];
    authorizeSelected.value = [];
  };

  const handleShowAuthorize = (selected: SqlServerHaModel[]) => {
    isShowAuthorize.value = true;
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

  const handleQuickSearchChange = () => {
    fetchData();
    tableRef.value?.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .sqlserver-ha-cluster-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
