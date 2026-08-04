<template>
  <div class="sqlserver-ha-cluster-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'sqlserver.haClusterList.instanceApply'"
        action-id="sqlserver_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'sqlserver.haClusterList.batchOperation'"
        :cluster-type="ClusterTypes.SQLSERVER_HA"
        :selected="selectedList"
        @success="fetchData" />
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
        <OperationColumn
          ref="operationColumnRef"
          :cluster-type="ClusterTypes.SQLSERVER_HA">
          <template #default="{ data }: { data: SqlServerHaModel }">
            <template v-if="data.isOnline">
              <div v-db-console="'sqlserver.haClusterList.authorize'">
                <AuthButton
                  action-id="sqlserver_authorize"
                  :permission="data.permission.sqlserver_authorize"
                  :resource="data.id"
                  text
                  @click="handleShowAuthorize([data])">
                  {{ t('授权') }}
                </AuthButton>
              </div>
              <ClusterAlarmSubscribe
                :data="data"
                db-console-prefix="sqlserver.haClusterList"
                @click="hideOperationColumn"
                @edit="(e) => handleToDetails(data.id, e, 'alarmSubscription')" />
            </template>
            <div
              v-if="data.isOnline"
              v-db-console="'sqlserver.haClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="sqlserver_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.sqlserver_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-else
              v-db-console="'sqlserver.haClusterList.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="sqlserver_enable_disable"
                  :disabled="data.isStarting"
                  :permission="data.permission.sqlserver_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'sqlserver.haClusterList.reset'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    placement: 'right',
                    disabled: data.isOffline,
                    content: t('重置前需先禁用集群'),
                  }"
                  action-id="sqlserver_manage"
                  :disabled="data.isOnline"
                  :permission="data.permission.sqlserver_manage"
                  :resource="data.id"
                  text
                  @click="handleResetCluster(data)">
                  {{ t('重置') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'sqlserver.haClusterList.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    placement: 'right',
                    disabled: data.isOffline,
                    content: t('删除前需先禁用集群'),
                  }"
                  action-id="sqlserver_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.sqlserver_destroy"
                  :resource="data.id"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <ClusterDomainDnsRelation
              v-if="data.isOnline"
              :data="data" />
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
        <TableColumn
          col-key="sync_mode"
          :title="t('同步模式')"
          :width="120">
          <template #default="{ row }: { row: SqlServerHaModel }">
            {{ row.sync_mode || '--' }}
          </template>
        </TableColumn>
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
<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterAlarmSubscribe from '@views/db-manage/common/cluster-alarm-subscribe/Index.vue';
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

  const operationColumnRef = ref<ComponentExposed<typeof OperationColumn>>();
  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
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

  const hideOperationColumn = () => {
    operationColumnRef.value?.hide();
  };

  const handleResetCluster = (data: SqlServerHaModel) => {
    currentData.value = data;
    isShowClusterReset.value = true;
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
      name: TicketTypes.SQLSERVER_HA_APPLY,
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: String(route.name),
      },
    });
  };

  const handleQuickSearchChange = () => {
    fetchData();
    // tableRef.value?.clearSelected();
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
