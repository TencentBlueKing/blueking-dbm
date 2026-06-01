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
  <div class="mysql-ha-instance-list-page">
    <div class="operation-box">
      <InstanceBatchCopy
        v-db-console="'mysql.haInstanceManage.batchCopy'"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        v-db-console="'mysql.haInstanceManage.batchCopy'"
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DropdownExportExcel
        v-db-console="'mysql.haInstanceManage.export'"
        class="ml-8"
        export-type="instance"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="tendbha" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <InstanceTable
      ref="instanceTable"
      :bk-ui-settings="settings"
      :cluster-type="ClusterTypes.TENDBHA"
      :data-source="getTendbhaInstanceList"
      :filter-value="quickSearchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #instanceAddress>
        <InstanceAddressColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
          <template #append="{ data }: { data: TendbhaInstanceModel }">
            <BkTag
              v-if="data.role === 'backend_slave' && data.is_stand_by"
              class="cluster-specific-flag ml-4"
              size="small">
              Standby
            </BkTag>
          </template>
        </InstanceAddressColumn>
      </template>
      <template #relatedCluster>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </MasterDomainColumn>
      </template>
      <template #ip>
        <IpColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </IpColumn>
      </template>
    </InstanceTable>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  import { useInstanceQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import InstanceTable, {
    InstanceAddressColumn,
    IpColumn,
    MasterDomainColumn,
  } from '@views/db-manage/common/instance-table/Index.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  const { t } = useI18n();

  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<TendbhaInstanceModel>();
  const { isSearching, quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_type: ClusterTypes.TENDBHA,
  });
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS, {
    disabled: ['instance_address'],
  });

  const instanceTableRef = useTemplateRef('instanceTable');

  const getTableInstance = () => instanceTableRef.value;

  const getBatchCopyData = () => {
    return instanceTableRef.value!.getAllData<TendbhaInstanceModel>();
  };

  const fetchData = () => {
    instanceTableRef.value!.fetchData(quickSearchValue.value);
  };

  const handleQuickSearchChange = () => {
    fetchData();
    // instanceTableRef.value!.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };
</script>

<style lang="less">
  .mysql-ha-instance-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
