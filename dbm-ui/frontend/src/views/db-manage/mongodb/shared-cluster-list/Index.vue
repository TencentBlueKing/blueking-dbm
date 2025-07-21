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
        :selected="selected"
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
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <ClusterIpCopy
        v-db-console="'mongodb.sharedClusterList.batchCopy'"
        :selected="selected" />
      <TagSearch @search="handleTagSearch" />
      <DbSearchSelect
        class="header-action-search-select"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <ClusterTable
      ref="tableRef"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
      :data-source="getMongoList"
      :settings="tableSetting"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER">
          <template #default="{ data }">
            <div v-db-console="'mongodb.sharedClusterList.getAccess'">
              <BkButton
                :disabled="data.isOffline"
                text
                @click="handleShowAccessEntry(data)">
                {{ t('获取访问方式') }}
              </BkButton>
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
          :is-filter="isFilter"
          :label="t('访问入口')"
          :selected-list="selected"
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
          :is-filter="isFilter"
          label="ConfigSvr"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="mongos"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Mongos"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
          field="mongodb"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="ShardSvr"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
  </div>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.MONGODB"
    :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
    :selected="selected"
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
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

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
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ShardClusterDetail from '@views/db-manage/mongodb/common/shared-cluster-detail/Index.vue';
  import AccessEntry from '@views/db-manage/mongodb/components/AccessEntry.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.MONGODB,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleAddClb } = useAddClb<{ cluster_id: number }>(ClusterTypes.MONGO_SHARED_CLUSTER);
  const {
    batchSearchIpInatanceList,
    clearSearchValue,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    isFilter,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(),
    searchType: ClusterTypes.MONGO_SHARED_CLUSTER,
  });
  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('MongoDBSharedClusterDetail');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const clusterAuthorizeShow = ref(false);
  const excelAuthorizeShow = ref(false);
  const selected = ref<MongodbModel[]>([]);
  const accessEntryInfoShow = ref(false);
  const accessEntryInfo = ref<MongodbModel | undefined>();
  const tagSearchValue = ref<Record<string, any>>({});

  const getTableInstance = () => tableRef.value;

  const searchSelectData = computed(() => [
    {
      async: false,
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      async: false,
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'cluster_ids',
      multiple: true,
      name: 'ID',
    },
    {
      async: false,
      id: 'name',
      multiple: true,
      name: t('集群名称'),
    },
    {
      children: searchAttrs.value.bk_cloud_id,
      id: 'bk_cloud_id',
      multiple: true,
      name: t('管控区域'),
    },
    {
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.major_version,
      id: 'major_version',
      multiple: true,
      name: t('版本'),
    },
    {
      children: searchAttrs.value.region,
      id: 'region',
      multiple: true,
      name: t('地域'),
    },
    {
      id: 'creator',
      name: t('创建人'),
    },
    {
      children: searchAttrs.value.time_zone,
      id: 'time_zone',
      multiple: true,
      name: t('时区'),
    },
  ]);

  const tableDataList = computed(() => tableRef.value?.getData<MongodbModel>() || []);
  const hasData = computed(() => tableDataList.value.length > 0);
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.MONGODB_SHARED_CLUSTER_SETTINGS,
    {
      checked: [
        'cluster_name',
        'master_domain',
        'status',
        'cluster_stats',
        'major_version',
        'disaster_tolerance_level',
        'region',
        'mongo_config',
        'mongos',
        'mongodb',
        'tag',
      ],
      disabled: ['master_domain'],
    },
  );

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then((res) =>
        res.results.map((item) => ({
          id: item.username,
          name: item.username,
        })),
      );
    }

    // 不需要远层加载
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

  const handleApply = () => {
    router.push({
      name: 'MongoDBSharedClusterApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleSelection = (key: unknown, list: MongodbModel[]) => {
    selected.value = list;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleClearSelected = () => {
    selected.value = [];
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

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchData();
  };

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValue.value),
      cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
      ...tagSearchValue.value,
      ...sortValue,
    });
  };
</script>
<style lang="less">
  .mongodb-shared-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;

      .tag-search-main {
        margin-left: auto;
      }

      .header-action-search-select {
        flex: 1;
        max-width: 500px;
      }

      .header-action-deploy-time {
        width: 300px;
        margin-left: 8px;
      }
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
