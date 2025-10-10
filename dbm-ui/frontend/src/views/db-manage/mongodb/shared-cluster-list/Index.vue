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
  <div class="mongodb-shared-cluster-list-page">
    <div class="header-action">
      <BkButton
        v-db-console="'mongodb.sharedClusterList.instanceApply'"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </BkButton>
      <ClusterBatchOperation
        v-db-console="'mongodb.sharedClusterList.batchOperation'"
        :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
        :selected="selectedList"
        @success="fetchData" />
      <span
        v-bk-tooltips="{
          disabled: hasData,
          content: t('请先申请集群'),
        }"
        v-db-console="'mongodb.sharedClusterList.importAuthorize'"
        class="inline-block">
        <BkButton
          :disabled="!hasData"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
      </span>
      <DropdownExportExcel
        v-db-console="'mongodb.sharedClusterList.export'"
        :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="mongodb" />
      <ClusterIpCopy
        v-db-console="'mongodb.sharedClusterList.batchCopy'"
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
      :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
      :data-source="getMongoList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER">
          <template #default="{ data }: { data: MongodbModel }">
            <div v-db-console="'mongodb.sharedClusterList.getAccess'">
              <BkButton
                :disabled="data.isOffline"
                text
                @click="handleShowAccessEntry(data)">
                {{ t('获取访问方式') }}
              </BkButton>
            </div>
            <div v-db-console="'mongodb.sharedClusterList.queryAccessSource'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="mongodb_source_access_view"
                  :disabled="data.isOffline"
                  :permission="data.permission.mongodb_source_access_view"
                  :resource="data.id"
                  style="width: 100%; height: 32px"
                  text
                  @click="handleGoQueryAccessSourcePage(data.master_domain)">
                  {{ t('查询访问来源') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'mongodb.sharedClusterList.webconsole'">
              <AuthRouterLink
                action-id="mongodb_webconsole"
                :disabled="data.isOffline"
                :permission="data.permission.mongodb_webconsole"
                :resource="data.id"
                target="_blank"
                :to="{
                  name: 'MongodbWebconsole',
                  query: {
                    clusterId: data.id,
                  },
                }">
                Webconsole
              </AuthRouterLink>
            </div>
            <div v-db-console="'mongodb.sharedClusterList.scaleUpDown'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isOffline || data.operationDisabled"
                  text
                  @click="handleToCapacityChange(data)">
                  {{ t('集群容量变更') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlineCLB"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="mongodb_plugin_create_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.mongodb_plugin_create_clb"
                  :resource="data.id"
                  text
                  @click="() => handleAddClb({ details: { cluster_id: data.id } })">
                  {{ t('启用CLB') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'mongodb.sharedClusterList.enable'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isStarting || data.isOnline"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnline"
              v-db-console="'mongodb.sharedClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  :disabled="data.isOffline || Boolean(data.operationTicketId)"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'mongodb.sharedClusterList.delete'">
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
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData">
          <template #append="{ data }">
            <ClusterEntryPanel
              v-if="data.isOnlineCLB"
              :cluster-id="data.id"
              entry-type="clb" />
          </template>
        </MasterDomainColumn>
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="mongo_config"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="ConfigSvr"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="mongos"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Mongos"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="mongodb"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="ShardSvr"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
  </div>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MONGODB"
    :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
    :selected="selectedList"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
    :ticket-type="TicketTypes.MONGODB_EXCEL_AUTHORIZE" />
  <AccessEntry
    v-if="accessEntryInfo"
    v-model:is-show="accessEntryInfoShow"
    :data="accessEntryInfo" />
  <TableDetailDialog
    v-model="isShowDetail"
    :default-offset-left="300"
    @close="handleDetailClose">
    <ShardClusterDetail
      v-if="clusterId"
      :cluster-id="clusterId" />
  </TableDetailDialog>
</template>

<script setup lang="tsx">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useAddClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import AccessEntry from '@views/db-manage/mongodb/common/cluster-operations/AccessEntry.vue';
  import ShardClusterDetail from '@views/db-manage/mongodb/common/shared-cluster-detail/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.MONGO_SHARED_CLUSTER);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.MONGODB,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleAddClb } = useAddClb<{ cluster_id: number }>(ClusterTypes.MONGO_SHARED_CLUSTER);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('MongoDBSharedClusterDetail');
  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<MongodbModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const clusterAuthorizeShow = ref(false);
  const excelAuthorizeShow = ref(false);
  const accessEntryInfoShow = ref(false);
  const accessEntryInfo = ref<MongodbModel | undefined>();

  const getTableInstance = () => tableRef.value;

  const tableDataList = computed(() => tableRef.value?.getData<MongodbModel>() || []);
  const hasData = computed(() => tableDataList.value.length > 0);

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.MONGODB_SHARED_CLUSTER_SETTINGS,
    {
      disabled: ['master_domain'],
    },
  );

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
      name: 'MongoDBSharedClusterApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleClearSelected = () => {
    selectedList.value = [];
  };

  const handleShowAccessEntry = (data: MongodbModel) => {
    accessEntryInfo.value = data;
    accessEntryInfoShow.value = true;
  };

  const handleToCapacityChange = (row: MongodbModel) => {
    const routeInfo = router.resolve({
      name: TicketTypes.MONGODB_SCALE_UPDOWN,
      query: {
        masterDomain: row.master_domain,
      },
    });
    window.open(routeInfo.href, '_blank');
  };

  const handleGoQueryAccessSourcePage = (masterDomain: string) => {
    const routeInfo = router.resolve({
      name: 'MongodbQueryAccessSource',
      query: {
        masterDomain,
      },
    });
    window.open(routeInfo.href, '_blank');
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .mongodb-shared-cluster-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }

  .info-box-cluster-name {
    color: #313238;
  }

  .cluster-delete-content {
    padding-left: 16px;
    text-align: left;
    word-break: break-all;
  }
</style>
