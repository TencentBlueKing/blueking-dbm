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
  <div class="oracle-ha-cluster-list-page">
    <div class="operation-box">
      <DropdownExportExcel
        v-db-console="'oracle.haClusterList.export'"
        :ids="selectedIdList"
        type="oracle_primary_standby" />
      <ClusterIpCopy
        v-db-console="'oracle.haClusterList.batchCopy'"
        class="ml-8"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
      :data-source="getOracleHaClusterList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY">
          <template #default="{ data }: { data: OracleHaModel }">
            <div v-db-console="'oracle.toolbox.sqlExecute'">
              <OperationBtnStatusTips :data="data">
                <RouterLink
                  target="_blank"
                  :to="{
                    name: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
                    query: {
                      masterDomain: data.master_domain,
                    },
                  }">
                  {{ t('变更 SQL 执行') }}
                </RouterLink>
              </OperationBtnStatusTips>
            </div>
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
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
          :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
          field="primaries"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Primary"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
          field="standbys"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Standby"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
        </RoleColumn>
      </template>
    </ClusterTable>
  </div>
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

  import OracleHaModel from '@services/model/oracle/oracle-ha';
  import { getOracleHaClusterList } from '@services/source/oracleHaCluster';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
    SlaveDomainColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/oracle/common/ha-cluster-detail/Index.vue';

  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.ORACLE_PRIMARY_STANDBY);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('OracleHaDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<OracleHaModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');

  const getTableInstance = () => tableRef.value;

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.ORACLE_HA_CLUSTER_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchData = () => {
    tableRef.value!.fetchData(searchValue.value);
  };

  watch(searchValue, () => {
    setTimeout(() => {
      fetchData();
      tableRef.value!.clearSelected();
    });
  });

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>

<style lang="less">
  .oracle-ha-cluster-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
