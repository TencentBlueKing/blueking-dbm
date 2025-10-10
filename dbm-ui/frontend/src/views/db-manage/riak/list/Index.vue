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
  <div class="riak-cluster-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'riak.clusterManage.instanceApply'"
        action-id="riak_cluster_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'riak.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.RIAK"
        :selected="selectedList"
        @success="fetchData" />
      <DropdownExportExcel
        v-db-console="'riak.clusterManage.export'"
        :ids="selectedIdList"
        type="riak" />
      <ClusterIpCopy
        v-db-console="'riak.clusterManage.batchCopy'"
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
      :bk-ui-settings="tableSetting"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.RIAK"
      :data-source="getRiakList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.RIAK">
          <template #default="{ data }: { data: RiakModel }">
            <div v-db-console="'riak.clusterManage.addNodes'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="riak_cluster_scale_in"
                  class="mr-8"
                  :disabled="data.isOffline"
                  :permission="data.permission.riak_cluster_scale_in"
                  :resource="data.id"
                  text
                  @click="handleAddNodes(data)">
                  {{ t('添加节点') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'riak.clusterManage.deleteNodes'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="riak_cluster_scale_out"
                  class="mr-8"
                  :disabled="data.isOffline"
                  :permission="data.permission.riak_cluster_scale_out"
                  :resource="data.id"
                  text
                  @click="handleDeleteNodes(data)">
                  {{ t('删除节点') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'riak.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="riak_enable_disable"
                  class="mr-8"
                  :disabled="data.isOffline || Boolean(data.operationTicketId)"
                  :permission="data.permission.riak_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'riak.clusterManage.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="riak_enable_disable"
                  :disabled="data.isOnline || data.isStarting"
                  :permission="data.permission.riak_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'riak.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="riak_cluster_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.riak_cluster_destroy"
                  :resource="data.id"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <ClusterDomainDnsRelation :data="data" />
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.RIAK"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('主访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.RIAK"
          field="riak_node"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
      <template #moduleNames>
        <ModuleNameColumn :cluster-type="ClusterTypes.RIAK" />
      </template>
    </ClusterTable>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="addNodeShow"
      quick-close
      :title="t('添加节点【xx】', [detailData.cluster_name])"
      :width="960">
      <AddNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="deleteNodeShow"
      :title="t('删除节点【xx】', [detailData.cluster_name])"
      :width="960">
      <DeleteNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
    <TableDetailDialog
      v-model="isShowDetail"
      :default-offset-left="300"
      @close="handleDetailClose">
      <ClusterDetail
        v-if="clusterId"
        :cluster-id="clusterId" />
    </TableDetailDialog>
  </div>
</template>
<script setup lang="tsx">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RiakModel from '@services/model/riak/riak';
  import { getRiakList } from '@services/source/riak';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    ModuleNameColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/riak/common/cluster-detail/Index.vue';

  import AddNodes from './components/AddNodes.vue';
  import DeleteNodes from './components/DeleteNodes.vue';

  const router = useRouter();
  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.RIAK);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(ClusterTypes.RIAK, {
    onSuccess: () => fetchData(),
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('riakDetail');

  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<RiakModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const detailData = ref<RiakModel>();

  const getTableInstance = () => tableRef.value;

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.RIAK_TABLE_SETTINGS, {
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

  const handleApply = () => {
    router.push({
      name: 'RiakApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
      },
    });
  };

  const handleAddNodes = (data: RiakModel) => {
    detailData.value = data;
    addNodeShow.value = true;
  };

  const handleDeleteNodes = (data: RiakModel) => {
    detailData.value = data;
    deleteNodeShow.value = true;
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .riak-cluster-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
