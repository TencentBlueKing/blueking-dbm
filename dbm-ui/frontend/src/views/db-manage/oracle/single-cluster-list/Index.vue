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
  <div class="oracle-single-cluster-list-page">
    <div class="operation-box">
      <DropdownExportExcel
        v-db-console="'oracle.singleClusterList.export'"
        :ids="selectedIds"
        type="oracle_single_none" />
      <ClusterIpCopy
        v-db-console="'oracle.singleClusterList.batchCopy'"
        class="ml-8"
        :selected="selected" />
      <TagSearch
        style="margin-left: auto"
        @search="handleTagSearch" />
      <DbSearchSelect
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div class="table-wrapper">
      <ClusterTable
        ref="tableRef"
        :cluster-id="clusterId"
        :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE"
        :data-source="getOracleSingleClusterList"
        :settings="settings"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings">
        <template #operation>
          <OperationColumn :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE">
            <template #default="{ data }">
              <div v-db-console="'oracle.toolbox.sqlExecute'">
                <OperationBtnStatusTips :data="data">
                  <RouterLink
                    target="_blank"
                    :to="{
                      name: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
                      query: {
                        masterDomain: data.master_domain,
                      },
                    }">
                    {{ t('变更 SQL 执行') }}
                  </RouterLink>
                </OperationBtnStatusTips>
              </div>
            </template>
          </OperationColumn>
        </template>
        <template #masterDomain>
          <MasterDomainColumn
            :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE"
            field="master_domain"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            :label="t('主访问入口')"
            :selected-list="selected"
            @go-detail="handleToDetails"
            @refresh="fetchData" />
        </template>
        <template #role>
          <RoleColumn
            :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE"
            field="primaries"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            label="Primary"
            :search-ip="batchSearchIpInatanceList"
            :selected-list="selected"
            @go-detail="handleToDetails" />
        </template>
      </ClusterTable>
    </div>
  </div>
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
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import OracleSingleModel from '@services/model/oracle/oracle-single';
  import { getOracleSingleClusterList } from '@services/source/oracleSingleCluster';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/oracle/common/single-cluster-detail/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const { t } = useI18n();
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
    searchType: ClusterTypes.ORACLE_SINGLE_NONE,
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('OracleSingleDetail');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isInit = ref(false);
  const selectedClusterList = ref<OracleSingleModel[]>([]);
  const tagSearchValue = ref<Record<string, any>>({});
  const selected = ref<OracleSingleModel[]>([]);

  const getTableInstance = () => tableRef.value;

  const selectedIds = computed(() => selected.value.map((item) => item.id));

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

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.ORACLE_HA_CLUSTER_SETTINGS, {
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      'primary',
      'major_version',
      'disaster_tolerance_level',
      'region',
      // 'bk_cloud_id',
    ],
    disabled: ['master_domain'],
  });

  watch(searchValue, () => {
    setTimeout(() => {
      tableRef.value!.clearSelected();
    });
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

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValue.value),
      ...tagSearchValue.value,
      ...sortValue,
    });
    isInit.value = false;
  };

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchData();
  };

  const handleSelection = (data: any, list: OracleSingleModel[]) => {
    selected.value = list;
    selectedClusterList.value = list;
  };
</script>

<style lang="less">
  .oracle-single-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operation-box {
      display: flex;
      margin-bottom: 16px;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: 8px;
      }
    }
  }
</style>
