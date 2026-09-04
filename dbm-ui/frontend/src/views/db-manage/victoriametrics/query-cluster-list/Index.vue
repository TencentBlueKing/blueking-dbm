<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->
<template>
  <div class="victoriametrics-query-list-page">
    <div class="operation-box">
      <AuthButton
        v-db-console="'victoriametrics.queryClusterList.instanceApply'"
        action-id="k8s_victoriametrics_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        v-db-console="'victoriametrics.queryClusterList.export'"
        :has-selected="isSelected"
        :ids="selectedIdList"
        :type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT" />
      <DbQuickSearch
        v-model="searchValue"
        class="quick-search"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
      :data-source="getVictoriametricsQueryList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT">
          <template #default="{ data }: { data: VictoriametricsQueryModel }">
            <div
              v-if="data.isOnline"
              v-db-console="'victoriametrics.queryClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="k8s_vm_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.k8s_vm_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnline"
              v-db-console="'victoriametrics.queryClusterList.restart'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="k8s_victoriametrics_manage"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.k8s_victoriametrics_manage"
                  :resource="data.id"
                  text
                  @click="handleClusterRestart(data)">
                  {{ t('重启') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'victoriametrics.queryClusterList.enable'">
              <OperationBtnStatusTips
                :data="data"
                style="width: 100%">
                <AuthButton
                  action-id="k8s_vm_enable_disable"
                  :disabled="data.isStarting"
                  :permission="data.permission.k8s_vm_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'victoriametrics.queryClusterList.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                    placement: 'right',
                  }"
                  action-id="k8s_victoriametrics_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.k8s_victoriametrics_destroy"
                  :resource="data.id"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
          field="domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('查询入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
      </template>
    </ClusterTable>
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

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import VictoriametricsQueryModel from '@services/model/victoriametrics/victoriametrics-query';
  import { getVictoriametricsQueryList } from '@services/source/victoriametricsQuery';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterTable, { MasterDomainColumn, OperationColumn } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useK8sClusterRestart, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/victoriametrics/common/query-cluster-detail/Index.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.K8S_VICTORIAMETRICS_SELECT);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.K8S_VICTORIAMETRICS,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleClusterRestart } = useK8sClusterRestart(ClusterTypes.K8S_VICTORIAMETRICS, {
    onSuccess: () => fetchData(),
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('VictoriametricsQueryDetail');

  const { handleSelection, isSelected, selectedIdList, selectedList } =
    useClusterTableSelect<VictoriametricsQueryModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');

  const getTableInstance = () => tableRef.value;

  // 设置用户个人表头信息
  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.VICTORIAMETRICS_QUERY_TABLE_SETTINGS,
    {
      disabled: ['domain'],
    },
  );

  const fetchData = () => {
    tableRef.value!.fetchData(searchValue.value);
  };

  /** 申请实例 */
  const handleApply = () => {
    router.push({
      name: TicketTypes.K8S_VICTORIAMETRICS_SELECT_APPLY,
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>

<style lang="less">
  .victoriametrics-query-list-page {
    .operation-box {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }

    .quick-search {
      width: 500px;
      margin-left: auto;
    }
  }
</style>
