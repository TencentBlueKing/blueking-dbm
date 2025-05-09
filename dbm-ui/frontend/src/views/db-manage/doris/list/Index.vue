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
        :selected="selected"
        @success="fetchTableData" />
      <DropdownExportExcel
        v-db-console="'doris.clusterManage.batchOperation'"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="doris" />
      <ClusterIpCopy
        v-db-console="'doris.clusterManage.batchCopy'"
        :selected="selected" />
      <TagSearch @search="handleTagSearch" />
      <DbSearchSelect
        :data="serachData"
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
      :cluster-type="ClusterTypes.DORIS"
      :data-source="getDorisList"
      :settings="tableSetting"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.DORIS">
          <template #default="{ data }">
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
          :is-filter="isFilter"
          :label="t('访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchTableData" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_follower"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('Follower节点')"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_observer"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('Observer节点')"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_backend_hot"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('热节点')"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.DORIS"
          field="doris_backend_cold"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('冷节点')"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      :title="t('xx扩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
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
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import { getDorisList } from '@services/source/doris';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

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
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
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
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchTableData(),
    searchType: ClusterTypes.DORIS,
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const tagSearchValue = ref<Record<string, any>>({});

  const selected = shallowRef<DorisModel[]>([]);
  const operationData = shallowRef<DorisModel>();

  const getTableInstance = () => tableRef.value;

  const serachData = computed(() => [
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
      id: 'name',
      name: t('集群名称'),
    },
    {
      children: searchAttrs.value.bk_cloud_id,
      id: 'bk_cloud_id',
      multiple: true,
      name: t('管控区域'),
    },
    {
      id: 'creator',
      name: t('创建人'),
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
      children: searchAttrs.value.time_zone,
      id: 'time_zone',
      multiple: true,
      name: t('时区'),
    },
  ]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.DORIS_TABLE_SETTINGS, {
    checked: [
      'domain',
      'cluster_name',
      'bk_cloud_id',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'status',
      'doris_follower',
      'doris_observer',
      'doris_backend_hot',
      'doris_backend_cold',
      'cluster_time_zone',
      'tag',
    ],
    disabled: ['domain'],
  });

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, serachData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return serachData.value.filter((item) => !selected.includes(item.id));
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
    return serachData.value.find((set) => set.id === item.id)?.children || [];
  };

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchTableData();
  };

  const fetchTableData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValue.value),
      ...tagSearchValue.value,
      ...sortValue,
    });
  };

  const handleSelection = (key: any, list: DorisModel[]) => {
    selected.value = list;
  };

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
</script>

<style lang="less">
  .doris-list-page {
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

      .bk-search-select {
        flex: 1;
        max-width: 500px;
      }
    }
  }
</style>
