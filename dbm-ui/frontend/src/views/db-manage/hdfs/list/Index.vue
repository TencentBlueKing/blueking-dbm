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
  <div class="hdfs-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'hdfs.clusterManage.instanceApply'"
        action-id="hdfs_apply"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'hdfs.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.HDFS"
        :selected="selectedList"
        @success="fetchData" />
      <DropdownExportExcel
        v-db-console="'hdfs.clusterManage.export'"
        :ids="selectedIdList"
        type="hdfs" />
      <ClusterIpCopy
        v-db-console="'hdfs.clusterManage.batchCopy'"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="tableSetting"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.HDFS"
      :data-source="dataSource"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn
          ref="operationColumnRef"
          :cluster-type="ClusterTypes.HDFS">
          <template #default="{ data }: { data: HdfsModel }">
            <div v-db-console="'hdfs.clusterManage.manage'">
              <a
                :href="data.access_url"
                target="_blank">
                WebUI
              </a>
            </div>
            <div v-db-console="'hdfs.clusterManage.getAccess'">
              <AuthButton
                action-id="hdfs_access_entry_view"
                :disabled="data.isOffline"
                :permission="data.permission.hdfs_access_entry_view"
                :resource="data.id"
                text
                @click="handleShowPassword(data)">
                {{ t('获取访问方式') }}
              </AuthButton>
            </div>
            <ClusterAlarmSubscribe
              :data="data"
              db-console-prefix="hdfs.clusterManage"
              @click="hideOperationColumn"
              @edit="(e) => handleToDetails(data.id, e, 'alarmSubscription')" />
            <div v-db-console="'hdfs.clusterManage.scaleUp'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="hdfs_scale_up"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.hdfs_scale_up"
                  :resource="data.id"
                  text
                  @click="handleShowExpansion(data)">
                  {{ t('扩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'hdfs.clusterManage.scaleDown'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="hdfs_shrink"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.hdfs_shrink"
                  :resource="data.id"
                  text
                  @click="handleShowShrink(data)">
                  {{ t('缩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'hdfs.clusterManage.viewAccessConfiguration'">
              <AuthButton
                action-id="hdfs_view"
                :disabled="data.isOffline"
                :permission="data.permission.hdfs_view"
                :resource="data.id"
                text
                @click="handleShowSettings(data)">
                {{ t('查看访问配置') }}
              </AuthButton>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'hdfs.clusterManage.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="hdfs_enable_disable"
                  class="mr-8"
                  :disabled="data.isStarting"
                  :permission="data.permission.hdfs_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-else
              v-db-console="'hdfs.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="hdfs_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.hdfs_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'hdfs.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="hdfs_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.hdfs_destroy"
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
          :cluster-type="ClusterTypes.HDFS"
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
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_namenode"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="NameNode"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_zookeeper"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Zookeeper"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_journalnode"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Journalnode"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_datanode"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="DataNode"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
    <ClusterExpansion
      v-if="operationData"
      v-model:is-show="isShowExpandsion"
      :cluster-data="operationData"
      @change="fetchData" />
    <ClusterShrink
      v-if="operationData"
      v-model:is-show="isShowShrink"
      :cluster-data="operationData"
      @change="fetchData" />
    <BkDialog
      v-model:is-show="isShowPassword"
      render-directive="if"
      :title="t('获取访问方式')"
      :width="500">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id"
        :db-type="DBTypes.HDFS" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
    <BkSideslider
      v-model:is-show="isShowSettings"
      class="settings-sideslider"
      quick-close
      render-directive="if"
      :title="t('查看访问配置')"
      :width="960">
      <ClusterSettings
        v-if="operationData"
        :cluster-id="operationData.id" />
    </BkSideslider>
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

  import HdfsModel from '@services/model/hdfs/hdfs';
  import { getHdfsList } from '@services/source/hdfs';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import ClusterAlarmSubscribe from '@views/db-manage/common/cluster-alarm-subscribe/Index.vue';
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
  import ClusterDetail from '@views/db-manage/hdfs/common/cluster-detail/Index.vue';
  import ClusterExpansion from '@views/db-manage/hdfs/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/hdfs/common/shrink/Index.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';

  import ClusterSettings from './components/cluster-settings/Index.vue';

  const route = useRoute();
  const { t } = useI18n();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.HDFS);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(ClusterTypes.HDFS, {
    onSuccess: () => fetchData(),
  });
  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('hdfsDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<HdfsModel>();

  const router = useRouter();

  const dataSource = getHdfsList;

  const operationColumnRef = ref<ComponentExposed<typeof OperationColumn>>();
  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isShowSettings = ref(false);

  const operationData = shallowRef<HdfsModel>();

  const getTableInstance = () => tableRef.value;

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.HDFS_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchData = () => {
    tableRef.value?.fetchData(searchValue.value);
  };

  // 集群提单
  const handleGoApply = () => {
    router.push({
      name: TicketTypes.HDFS_APPLY,
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const hideOperationColumn = () => {
    operationColumnRef.value?.hide();
  };

  // 扩容
  const handleShowExpansion = (clusterData: HdfsModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: HdfsModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  const handleShowPassword = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  const handleShowSettings = (clusterData: HdfsModel) => {
    operationData.value = clusterData;
    isShowSettings.value = true;
  };

  const handleQuickSearchChange = () => {
    fetchData();
    tableRef.value!.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .hdfs-list-page {
    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
    }
  }
</style>
