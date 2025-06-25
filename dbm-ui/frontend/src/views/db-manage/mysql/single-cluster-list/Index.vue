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
        :selected="selected"
        @success="fetchData" />
      <BkButton
        v-db-console="'mysql.singleClusterList.importAuthorize'"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'mysql.singleClusterList.export'"
        :ids="selectedIds"
        type="tendbsingle" />
      <ClusterIpCopy
        v-db-console="'mysql.singleClusterList.batchCopy'"
        :selected="selected" />
      <TagSearch @search="handleTagSearch" />
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
        :cluster-type="ClusterTypes.TENDBSINGLE"
        :data-source="getTendbsingleList"
        :settings="settings"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings">
        <template #operation>
          <OperationColumn :cluster-type="ClusterTypes.TENDBSINGLE">
            <template #default="{ data }">
              <div v-db-console="'mysql.singleClusterList.authorize'">
                <BkButton
                  :disabled="data.isOffline"
                  text
                  @click="handleShowAuthorize([data])">
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
            :is-filter="isFilter"
            :label="t('访问入口')"
            :selected-list="selected"
            @go-detail="handleToDetails"
            @refresh="fetchData" />
        </template>
        <template #role>
          <RoleColumn
            :cluster-type="ClusterTypes.TENDBSINGLE"
            field="masters"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            :label="t('实例')"
            :search-ip="batchSearchIpInatanceList"
            :selected-list="selected"
            @go-detail="handleToDetails" />
        </template>
        <template #moduleNames>
          <ModuleNameColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        </template>
      </ClusterTable>
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeState.isShow"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    :selected="authorizeState.selected"
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
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { getTendbsingleList } from '@services/source/tendbsingle';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

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
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/mysql/common/single-cluster-detail/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBSINGLE,
    {
      onSuccess: () => fetchData(),
    },
  );
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
    fetchDataFn: () => fetchData(),
    searchType: ClusterTypes.TENDBSINGLE,
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('tendbsingleDetail');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const showDataExportSlider = ref(false);
  const selected = ref<TendbsingleModel[]>([]);
  const currentData = ref<TendbsingleModel>();
  const tagSearchValue = ref<Record<string, any>>({});

  const getTableInstance = () => tableRef.value;

  const authorizeState = reactive({
    isShow: false,
    selected: [] as TendbsingleModel[],
  });

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
      children: searchAttrs.value.db_module_id,
      id: 'db_module_id',
      multiple: true,
      name: t('模块'),
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

  // 设置用户个人表头信息
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBSINGLE_TABLE_SETTINGS, {
    checked: ['master_domain', 'status', 'cluster_stats', 'masters', 'db_module_id', 'major_version', 'region', 'tag'],
    disabled: ['master_domain'],
  });

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

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchData();
  };

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...getSearchSelectorParams(searchValue.value),
      ...tagSearchValue.value,
      ...sortValue,
    });
  };

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
  const handleShowAuthorize = (selected: TendbsingleModel[] = []) => {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  };
  const handleClearSelected = () => {
    selected.value = [];
    authorizeState.selected = [];
  };
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleShowDataExportSlider = (data: TendbsingleModel) => {
    currentData.value = data;
    showDataExportSlider.value = true;
  };

  /**
   * 表格选中
   */

  const handleSelection = (data: any, list: TendbsingleModel[]) => {
    selected.value = list;
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .mysql-single-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operation-box {
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
