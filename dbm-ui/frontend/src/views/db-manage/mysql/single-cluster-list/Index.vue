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
  <div class="mysql-single-cluster-list-page">
    <div class="operation-box">
      <AuthButton
        v-db-console="'mysql.singleClusterList.instanceApply'"
        action-id="mysql_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'mysql.singleClusterList.batchOperation'"
        :cluster-type="ClusterTypes.TENDBSINGLE"
        :selected="selectedList"
        @success="fetchData" />
      <BkButton
        v-db-console="'mysql.singleClusterList.importAuthorize'"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'mysql.singleClusterList.export'"
        :ids="selectedIdList"
        type="tendbsingle" />
      <ClusterIpCopy
        v-db-console="'mysql.singleClusterList.batchCopy'"
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
      :cluster-type="ClusterTypes.TENDBSINGLE"
      :data-source="getTendbsingleList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.TENDBSINGLE">
          <template #default="{ data }: { data: TendbsingleModel }">
            <div v-db-console="'mysql.singleClusterList.authorize'">
              <BkButton
                :disabled="data.isOffline"
                text
                @click="handleShowAuthorize(data)">
                {{ t('授权') }}
              </BkButton>
            </div>
            <div v-db-console="'mysql.haClusterList.webconsole'">
              <AuthRouterLink
                action-id="mysql_webconsole"
                :disabled="data.operationDisabled"
                :permission="data.permission.mysql_webconsole"
                :resource="data.id"
                target="_blank"
                :to="{
                  name: 'MySQLWebconsole',
                  query: {
                    clusterId: data.id,
                  },
                }">
                Webconsole
              </AuthRouterLink>
            </div>
            <div v-db-console="'mysql.singleClusterList.exportData'">
              <AuthButton
                action-id="mysql_dump_data"
                class="mr-8"
                :disabled="data.isOffline"
                :permission="data.permission.mysql_dump_data"
                :resource="data.id"
                text
                @click="handleShowDataExportSlider(data)">
                {{ t('导出数据') }}
              </AuthButton>
            </div>
            <div
              v-if="data.isOnline"
              v-db-console="'mysql.singleClusterList.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="mysql_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.mysql_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'mysql.singleClusterList.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="mysql_enable_disable"
                  :disabled="data.isStarting"
                  :permission="data.permission.mysql_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'mysql.singleClusterList.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="mysql_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.mysql_destroy"
                  :resource="data.id"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <ClusterDomainDnsRelation :data="data">
              <BkButton text>
                {{ t('手动配置域名 DNS 记录') }}
              </BkButton>
            </ClusterDomainDnsRelation>
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBSINGLE"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBSINGLE"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('实例')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
      <template #moduleNames>
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
      </template>
    </ClusterTable>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-if="currentData"
    v-model="isShowAuthorize"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    :selected="[currentData]"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBSINGLE" />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="showDataExportSlider"
    :data="currentData"
    :ticket-type="TicketTypes.MYSQL_DUMP_DATA" />
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

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { getTendbsingleList } from '@services/source/tendbsingle';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    ModuleNameColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/mysql/common/single-cluster-detail/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.TENDBSINGLE);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBSINGLE,
    {
      onSuccess: () => fetchData(),
    },
  );

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('tendbsingleDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<TendbsingleModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const isShowExcelAuthorize = ref(false);
  const showDataExportSlider = ref(false);
  const isShowAuthorize = ref(false);
  const currentData = ref<TendbsingleModel>();

  const getTableInstance = () => tableRef.value;

  // 设置用户个人表头信息
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBSINGLE_TABLE_SETTINGS, {
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

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplySingle',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  /** 集群授权 */
  const handleShowAuthorize = (data: TendbsingleModel) => {
    isShowAuthorize.value = true;
    currentData.value = data;
  };

  const handleClearSelected = () => {
    selectedList.value = [];
  };

  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleShowDataExportSlider = (data: TendbsingleModel) => {
    currentData.value = data;
    showDataExportSlider.value = true;
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .mysql-single-cluster-list-page {
    .operation-box {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
