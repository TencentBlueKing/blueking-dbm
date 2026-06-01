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
  <div class="tendbcluster-instance-list-page">
    <div class="operation-box">
      <InstanceBatchCopy
        v-db-console="'tendbCluster.instanceManage.batchCopy'"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        v-db-console="'tendbCluster.instanceManage.batchCopy'"
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DropdownExportExcel
        v-db-console="'tendbCluster.instanceManage.export'"
        class="ml-8"
        export-type="instance"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="spider" />
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
      :cluster-type="ClusterTypes.TENDBCLUSTER"
      :data-source="getTendbclusterInstanceList"
      :filter-value="quickSearchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @request-success="handleRequestSuccess"
      @selection="handleSelection">
      <template #instanceAddress>
        <InstanceAddressColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
          <template #append="{ data }: { data: TendbclusterInstanceModel }">
            <BkTag
              v-if="clusterPrimaryMap[data.ip]"
              class="cluster-specific-flag ml-4"
              size="small">
              Primary
            </BkTag>
          </template>
        </InstanceAddressColumn>
      </template>
      <template #relatedCluster>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </MasterDomainColumn>
      </template>
      <template #ip>
        <IpColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </IpColumn>
      </template>
    </InstanceTable>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { getTendbclusterInstanceList, getTendbclusterPrimary } from '@services/source/tendbcluster';
  import type { ListBase } from '@services/types';

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

  const { isSearching, quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_type: ClusterTypes.TENDBCLUSTER,
  });
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBCLUSTER_INSTANCE_TABLE, {
    disabled: ['instance_address'],
  });

  const { handleSelection, isSelected, selectedIdList, selectedList } =
    useClusterTableSelect<TendbclusterInstanceModel>();

  const instanceTableRef = useTemplateRef('instanceTable');

  const clusterPrimaryMap = shallowRef<Record<string, boolean>>({});

  const { run: rungGetTendbclusterPrimary } = useRequest(getTendbclusterPrimary, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        clusterPrimaryMap.value = data.reduce<Record<string, boolean>>((acc, cur) => {
          const ip = cur.primary.split(':')[0];
          if (ip) {
            Object.assign(acc, {
              [ip]: true,
            });
          }
          return acc;
        }, {});
      }
    },
  });

  const getTableInstance = () => instanceTableRef.value;

  const getBatchCopyData = () => {
    return instanceTableRef.value!.getAllData<TendbclusterInstanceModel>();
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

  const handleRequestSuccess = (data: ListBase<TendbclusterInstanceModel[]>) => {
    rungGetTendbclusterPrimary({
      cluster_ids: _.uniq(data.results.map((item) => item.cluster_id)),
    });
  };
</script>

<style lang="less">
  .tendbcluster-instance-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
