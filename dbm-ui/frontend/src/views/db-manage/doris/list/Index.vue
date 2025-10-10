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
  <div class="doris-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'doris.clusterManage.instanceApply'"
        action-id="doris_apply"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'doris.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.DORIS"
        :selected="selectedList"
        @success="fetchTableData" />
      <DropdownExportExcel
        v-db-console="'doris.clusterManage.batchOperation'"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="doris" />
      <ClusterIpCopy
        v-db-console="'doris.clusterManage.batchCopy'"
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
      :cluster-type="ClusterTypes.DORIS"
      :data-source="getDorisList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.DORIS">
          <template #default="{ data }: { data: DorisModel }">
            <div v-db-console="'doris.clusterManage.manage'">
              <a
                :href="data.access_url"
                target="_blank">
                WebUI
              </a>
            </div>
            <div v-db-console="'doris.clusterManage.getAccess'">
              <AuthButton
                action-id="doris_access_entry_view"
                :disabled="data.isOffline"
                :permission="data.permission.doris_access_entry_view"
                :resource="data.id"
                text
                @click="handleShowPassword(data)">
                {{ t('获取访问方式') }}
              </AuthButton>
            </div>
            <div v-db-console="'doris.clusterManage.scaleUp'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="doris_scale_up"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.doris_scale_up"
                  :resource="data.id"
                  text
                  @click="handleShowExpandsion(data)">
                  {{ t('扩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'doris.clusterManage.scaleDown'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="doris_shrink"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.doris_shrink"
                  :resource="data.id"
                  text
                  @click="handleShowShrink(data)">
                  {{ t('缩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnline"
              v-db-console="'doris.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="doris_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.doris_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-else
              v-db-console="'doris.clusterManage.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="doris_enable_disable"
                  :permission="data.permission.doris_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'doris.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="doris_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.doris_destroy"
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
          :cluster-type="ClusterTypes.DORIS"
          field="domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchTableData" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_follower"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('Follower节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_observer"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('Observer节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_backend_hot"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('热节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_backend_cold"
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
      :title="t('获取访问方式')">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id"
        :db-type="DBTypes.DORIS" />
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

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import { getDorisList } from '@services/source/doris';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterDetail from '@views/db-manage/doris/common/cluster-detail/Index.vue';
  import ClusterExpansion from '@views/db-manage/doris/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/doris/common/shrink/Index.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.DORIS);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.DORIS,
    {
      onSuccess: () => fetchTableData(),
    },
  );
  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('DorisDetail');

  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<DorisModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);

  const operationData = shallowRef<DorisModel>();

  const getTableInstance = () => tableRef.value;

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.DORIS_TABLE_SETTINGS, {
    disabled: ['domain'],
  });

  const fetchTableData = () => {
    tableRef.value!.fetchData(searchValue.value);
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
      name: 'DorisApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  // 扩容
  const handleShowExpandsion = (data: DorisModel) => {
    isShowExpandsion.value = true;
    operationData.value = data;
  };

  // 缩容
  const handleShowShrink = (data: DorisModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  const handleShowPassword = (clusterData: DorisModel) => {
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
  .doris-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
