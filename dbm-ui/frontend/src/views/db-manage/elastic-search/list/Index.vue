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
  <div class="es-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'es.clusterManage.instanceApply'"
        action-id="es_apply"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'es.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.ES"
        :selected="selectedList"
        @success="fetchTableData" />
      <DropdownExportExcel
        v-db-console="'es.clusterManage.export'"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="es" />
      <ClusterIpCopy
        v-db-console="'es.clusterManage.batchCopy'"
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
      :cluster-type="ClusterTypes.ES"
      :data-source="dataSource"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.ES">
          <template #default="{ data }: { data: EsModel }">
            <div v-db-console="'es.clusterManage.manage'">
              <a
                :href="data.access_url"
                target="_blank">
                Kibana
              </a>
            </div>
            <div v-db-console="'es.clusterManage.getAccess'">
              <AuthButton
                action-id="es_access_entry_view"
                :disabled="data.isOffline"
                :permission="data.permission.es_access_entry_view"
                :resource="data.id"
                text
                @click="handleShowPassword(data)">
                {{ t('获取访问方式') }}
              </AuthButton>
            </div>
            <div v-db-console="'es.clusterManage.scaleUp'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="es_scale_up"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.es_scale_up"
                  :resource="data.id"
                  text
                  @click="handleShowExpandsion(data)">
                  {{ t('扩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'es.clusterManage.scaleDown'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="es_shrink"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.es_shrink"
                  :resource="data.id"
                  text
                  @click="handleShowShrink(data)">
                  {{ t('缩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlineCLB"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="es_create_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.es_create_clb"
                  :resource="data.id"
                  text
                  @click="() => handleAddClb({ details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } })">
                  {{ t('启用接入层负载均衡（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlinePolaris"
              v-db-console="'common.polaris'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="es_create_polaris"
                  :disabled="data.isOffline"
                  :permission="data.permission.es_create_polaris"
                  :resource="data.id"
                  text
                  @click="() => handleAddPolaris({ details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } })">
                  {{ t('启用接入层负载均衡（北极星）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnlineCLB"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="es_dns_bind_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.es_dns_bind_clb"
                  :resource="data.id"
                  text
                  @click="
                    () =>
                      handleBindOrUnbindClb(
                        { details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } },
                        data.dns_to_clb,
                      )
                  ">
                  {{ data.dns_to_clb ? t('恢复主域名直连接入层') : t('配置主域名指向负载均衡器（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'es.clusterManage.enable'">
              <AuthButton
                action-id="es_enable_disable"
                :disabled="data.isStarting"
                :permission="data.permission.es_enable_disable"
                :resource="data.id"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </div>
            <div
              v-else
              v-db-console="'es.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="es_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.es_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'es.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="es_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.es_destroy"
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
          :cluster-type="ClusterTypes.ES"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchTableData">
          <template #append="{ data }">
            <div
              v-if="data.isOnlineCLB"
              class="ml-4">
              <ClusterEntryPanel
                :cluster-id="data.id"
                entry-type="clb" />
            </div>
            <div
              v-if="data.isOnlinePolaris"
              class="ml-4">
              <ClusterEntryPanel
                :cluster-id="data.id"
                entry-type="polaris"
                :panel-width="418" />
            </div>
          </template>
        </MasterDomainColumn>
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.ES"
          field="es_master"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('Master节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.ES"
          field="es_client"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('Client节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.ES"
          field="es_datanode_hot"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('热节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.ES"
          field="es_datanode_cold"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('冷节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
    <ClusterExpansion
      v-if="operationData"
      v-model:is-show="isShowExpandsion"
      :cluster-data="operationData"
      @change="fetchTableData" />
    <ClusterShrink
      v-if="operationData"
      v-model:is-show="isShowShrink"
      :cluster-data="operationData"
      @change="fetchTableData" />
    <BkDialog
      v-model:is-show="isShowPassword"
      render-directive="if"
      :title="t('获取访问方式')"
      :width="500">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id"
        :db-type="DBTypes.ES" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
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
  import { useRoute, useRouter } from 'vue-router';

  import EsModel from '@services/model/es/es';
  import { getEsList } from '@services/source/es';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

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
  import { useAddClb, useAddPolaris, useBindOrUnbindClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterDetail from '@views/db-manage/elastic-search/common/cluster-detail/Index.vue';
  import ClusterExpansion from '@views/db-manage/elastic-search/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/elastic-search/common/shrink/Index.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.ES);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(ClusterTypes.ES, {
    onSuccess: () => fetchTableData(),
  });
  const { handleAddClb } = useAddClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.ES);
  const { handleAddPolaris } = useAddPolaris<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.ES);
  const { handleBindOrUnbindClb } = useBindOrUnbindClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.ES);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('esDetail');
  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<EsModel>();

  const dataSource = getEsList;

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);

  const operationData = shallowRef<EsModel>();

  const getTableInstance = () => tableRef.value;

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.ES_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchTableData = () => {
    tableRef.value?.fetchData(searchValue.value);
  };

  watch(searchValue, () => {
    setTimeout(() => {
      fetchTableData();
      tableRef.value!.clearSelected();
    });
  });

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'EsApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  // 扩容
  const handleShowExpandsion = (data: EsModel) => {
    isShowExpandsion.value = true;
    operationData.value = data;
  };

  // 缩容
  const handleShowShrink = (data: EsModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  const handleShowPassword = (clusterData: EsModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchTableData();
  };
</script>
<style lang="less">
  .es-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
