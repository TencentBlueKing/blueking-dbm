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
  <div class="mysql-ha-cluster-list-page">
    <div class="operation-box">
      <AuthButton
        v-db-console="'mysql.haClusterList.instanceApply'"
        action-id="mysql_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'mysql.haClusterList.batchOperation'"
        class="ml-8"
        :cluster-type="ClusterTypes.TENDBHA"
        :selected="selectedList"
        @success="handleBatchOperationSuccess" />
      <BkButton
        v-db-console="'mysql.haClusterList.importAuthorize'"
        class="ml-8"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'mysql.haClusterList.export'"
        class="ml-8"
        :ids="selectedIdList"
        type="tendbha" />
      <ClusterIpCopy
        v-db-console="'mysql.haClusterList.batchCopy'"
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
      :cluster-type="ClusterTypes.TENDBHA"
      :data-source="getTendbhaList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.TENDBHA">
          <template #default="{ data }: { data: TendbhaModel }">
            <div v-db-console="'mysql.haClusterList.authorize'">
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
                :disabled="data.isOffline"
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
            <div v-db-console="'mysql.haClusterList.exportData'">
              <AuthButton
                action-id="mysql_dump_data"
                :disabled="data.isOffline"
                :permission="data.permission.mysql_dump_data"
                :resource="data.id"
                text
                @click="handleShowDataExportSlider(data)">
                {{ t('导出数据') }}
              </AuthButton>
            </div>
            <div
              v-if="isShowDumperEntry"
              v-db-console="'mysql.dataSubscription'">
              <AuthButton
                action-id="tbinlogdumper_install"
                :disabled="data.isOffline"
                :permission="data.permission.tbinlogdumper_install"
                :resource="data.id"
                text
                @click="handleShowCreateSubscribeRuleSlider(data)">
                {{ t('数据订阅') }}
              </AuthButton>
            </div>
            <div
              v-if="!data.isOnlineCLB"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="mysql_add_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.mysql_add_clb"
                  :resource="data.id"
                  text
                  @click="() => handleAddClb({ details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } })">
                  {{ t('启用接入层负载均衡（CLB）') }}
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
                  action-id="mysql_clb_bind_domain"
                  :disabled="data.isOffline"
                  :permission="data.permission.mysql_clb_bind_domain"
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
              v-if="data.isOnline"
              v-db-console="'mysql.haClusterList.disable'">
              <OperationBtnStatusTips
                :data="data"
                style="width: 100%">
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
              v-db-console="'mysql.haClusterList.enable'">
              <OperationBtnStatusTips
                :data="data"
                style="width: 100%">
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
            <div v-db-console="'mysql.haClusterList.delete'">
              <OperationBtnStatusTips
                :data="data"
                style="width: 100%">
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
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('主访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData">
          <template #append="{ data }">
            <div
              v-if="data.isOnlineCLB"
              class="ml-4">
              <ClusterEntryPanel
                :cluster-id="data.id"
                entry-type="clb" />
            </div>
          </template>
        </MasterDomainColumn>
      </template>
      <template #slaveDomain>
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="proxies"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Proxy"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Master"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="slaves"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Slave"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #nodeTag="{ data }">
            <BkTag
              v-if="data.is_stand_by"
              class="is-stand-by"
              size="small">
              Standby
            </BkTag>
          </template>
        </RoleColumn>
      </template>
      <template #moduleNames>
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBHA" />
      </template>
    </ClusterTable>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-if="currentData"
    v-model="isShowAuthorize"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave']"
    :selected="[currentData]"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBHA" />
  <CreateSubscribeRuleSlider
    v-if="currentData"
    v-model="isShowCreateSubscribeRule"
    :selected-clusters="[currentData]"
    show-tab-panel />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="isShowDataExport"
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

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { MySQLFunctions } from '@services/model/function-controller/functionController';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaList } from '@services/source/tendbha';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { useFunController } from '@stores';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
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
  import { useAddClb, useBindOrUnbindClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/mysql/common/ha-cluster-detail/Index.vue';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  const route = useRoute();
  const router = useRouter();
  const funControllerStore = useFunController();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.TENDBHA);
  const { t } = useI18n();
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleAddClb } = useAddClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.TENDBHA);
  const { handleBindOrUnbindClb } = useBindOrUnbindClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.TENDBHA);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('tendbHaDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<TendbhaModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const isShowExcelAuthorize = ref(false);
  const isShowCreateSubscribeRule = ref(false);
  const isShowDataExport = ref(false);
  const isShowAuthorize = ref(false);
  const currentData = ref<TendbhaModel>();

  const getTableInstance = () => tableRef.value;

  const isShowDumperEntry = computed(() => {
    const currentKey = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as MySQLFunctions;
    return funControllerStore.funControllerData.mysql.children[currentKey];
  });

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBHA_TABLE_SETTINGS, {
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

  const handleShowAuthorize = (data: TendbhaModel) => {
    isShowAuthorize.value = true;
    currentData.value = data;
  };

  const handleShowCreateSubscribeRuleSlider = (data: TendbhaModel) => {
    currentData.value = data;
    isShowCreateSubscribeRule.value = true;
  };

  const handleShowDataExportSlider = (data: TendbhaModel) => {
    currentData.value = data;
    isShowDataExport.value = true;
  };

  const handleClearSelected = () => {
    selectedList.value = [];
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  };
</script>

<style lang="less">
  .mysql-ha-cluster-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
