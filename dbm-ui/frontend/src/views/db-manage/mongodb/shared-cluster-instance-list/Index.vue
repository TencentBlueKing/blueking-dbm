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
  <div class="mongodb-instance-list-page">
    <div class="operation-box">
      <span
        v-bk-tooltips="{
          disabled: isSelected,
          content: t('请选择操作实例'),
        }">
        <BkButton
          class="w-88"
          :disabled="!isSelected"
          @click="handleChangeInstanceOnline(selectedList)">
          {{ t('批量重启') }}
        </BkButton>
      </span>
      <InstanceBatchCopy
        v-db-console="'mongodb.sharedClusterInstanceManage.batchCopy'"
        class="ml-8"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        v-db-console="'mongodb.sharedClusterInstanceManage.batchCopy'"
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DropdownExportExcel
        v-db-console="'mongodb.sharedClusterInstanceManage.export'"
        class="ml-8"
        export-type="instance"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="mongodb" />
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
      :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
      :data-source="dataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER">
          <template #default="{ data }: { data: MongodbInstanceModel }">
            <div v-db-console="'mongodb.sharedClusterInstanceManage.restartInstance'">
              <OperationBtnStatusTips :data="data">
                <BkButton
                  class="mr-8"
                  :disabled="data.isRebooting"
                  text
                  theme="primary"
                  @click="handleChangeInstanceOnline([data])">
                  {{ t('重启') }}
                </BkButton>
              </OperationBtnStatusTips>
            </div>
          </template>
        </OperationColumn>
      </template>
      <template #instanceAddress>
        <InstanceAddressColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </InstanceAddressColumn>
      </template>
      <template #domain>
        <InstanceDomainColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('域名')"
          :selected-list="selectedList">
        </InstanceDomainColumn>
      </template>
      <template #shard>
        <ShardColumn :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
      </template>
      <template #relatedCluster>
        <ClusterNameColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </ClusterNameColumn>
      </template>
      <template #ip>
        <IpColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </IpColumn>
      </template>
      <template #mongodbState>
        <MongodbStateColumn :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
      </template>
    </InstanceTable>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { getMongoInstancesList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useInstanceQuickSearch, useTableSettings, useTicketMessage } from '@hooks';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import InstanceTable, {
    ClusterNameColumn,
    InstanceAddressColumn,
    InstanceDomainColumn,
    IpColumn,
    MongodbStateColumn,
    OperationColumn,
    ShardColumn,
  } from '@views/db-manage/common/instance-table/Index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const { isSearching, quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
  });
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.MONGODB_SHARED_CLUSTER_INSTANCE, {
    disabled: ['instance_address'],
  });

  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<MongodbInstanceModel>();

  const instanceTableRef = useTemplateRef('instanceTable');

  const dataSource = (params: ServiceParameters<typeof getMongoInstancesList>) =>
    getMongoInstancesList({
      ...params,
      cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
    });

  const getTableInstance = () => instanceTableRef.value;

  const disableSelectMethod = (data: MongodbInstanceModel) => (data.isRebooting ? t('实例重启中') : false);

  const getBatchCopyData = () => {
    return instanceTableRef.value!.getAllData<MongodbInstanceModel>();
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

  const handleChangeInstanceOnline = (data: MongodbInstanceModel[]) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      contentAlign: 'center',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: () => {
        const params = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            infos: data.map((item) => ({
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              instance_id: item.id,
              port: item.port,
              role: item.role,
            })),
          },
          ticket_type: TicketTypes.MONGODB_INSTANCE_RELOAD,
        };
        return createTicket(params).then((res) => {
          ticketMessage(res.id);
          fetchData();
        });
      },
      subTitle: (
        <>
          {data.map((item) => (
            <div>{`${item.ip}:${item.port}`}</div>
          ))}
        </>
      ),
      title: t('确认重启实例？'),
    });
  };
</script>

<style lang="less">
  .mongodb-instance-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
