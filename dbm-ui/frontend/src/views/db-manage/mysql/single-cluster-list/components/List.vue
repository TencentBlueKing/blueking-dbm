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
        class="ml-8"
        :cluster-type="ClusterTypes.TENDBSINGLE"
        :selected="selected"
        @success="handleBatchOperationSuccess" />
      <BkButton
        v-db-console="'mysql.singleClusterList.importAuthorize'"
        class="ml-8"
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
      <DbSearchSelect
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :data-source="getTendbsingleList"
        releate-url-query
        :row-class="setRowClass"
        :row-config="{
          useKey: true,
          keyField: 'id',
        }"
        :scroll-y="{ enabled: true, gt: 0 }"
        selectable
        :settings="settings"
        :show-overflow="false"
        show-settings
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings">
        <IdColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBSINGLE"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
        <ClusterNameColumn
          :cluster-type="ClusterTypes.TENDBSINGLE"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected"
          @refresh="fetchData" />
        <StatusColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        <ClusterStatsColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBSINGLE"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('实例')"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        <CommonColumn :cluster-type="ClusterTypes.TENDBSINGLE" />
        <BkTableColumn
          :fixed="isStretchLayoutOpen ? false : 'right'"
          :label="t('操作')"
          :min-width="220"
          :show-overflow="false">
          <template #default="{data}: {data: TendbsingleModel}">
            <BkButton
              v-db-console="'mysql.singleClusterList.authorize'"
              class="mr-8"
              :disabled="data.isOffline"
              text
              theme="primary"
              @click="handleShowAuthorize([data])">
              {{ t('授权') }}
            </BkButton>
            <AuthRouterLink
              v-db-console="'mysql.haClusterList.webconsole'"
              action-id="mysql_webconsole"
              class="mr-8"
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
            <AuthButton
              v-db-console="'mysql.singleClusterList.exportData'"
              action-id="mysql_dump_data"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.mysql_dump_data"
              :resource="data.id"
              text
              theme="primary"
              @click="handleShowDataExportSlider(data)">
              {{ t('导出数据') }}
            </AuthButton>
            <MoreActionExtend v-db-console="'mysql.singleClusterList.moreOperation'">
              <BkDropdownItem
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
              </BkDropdownItem>
              <BkDropdownItem
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
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'mysql.singleClusterList.delete'">
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
              </BkDropdownItem>
            </MoreActionExtend>
          </template>
        </BkTableColumn>
      </DbTable>
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
</template>

<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { getTendbsingleList } from '@services/source/tendbsingle';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterNameColumn from '@views/db-manage/common/cluster-table-column/ClusterNameColumn.vue';
  import ClusterStatsColumn from '@views/db-manage/common/cluster-table-column/ClusterStatsColumn.vue';
  import CommonColumn from '@views/db-manage/common/cluster-table-column/CommonColumn.vue';
  import IdColumn from '@views/db-manage/common/cluster-table-column/IdColumn.vue';
  import MasterDomainColumn from '@views/db-manage/common/cluster-table-column/MasterDomainColumn.vue';
  import ModuleNameColumn from '@views/db-manage/common/cluster-table-column/ModuleNameColumn.vue';
  import RoleColumn from '@views/db-manage/common/cluster-table-column/RoleColumn.vue';
  import StatusColumn from '@views/db-manage/common/cluster-table-column/StatusColumn.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  interface ColumnData {
    cell: string;
    data: TendbsingleModel;
  }

  const clusterId = defineModel<number>('clusterId');

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBSINGLE,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const {
    searchAttrs,
    searchValue,
    sortValue,
    batchSearchIpInatanceList,
    isFilter,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBSINGLE,
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const showDataExportSlider = ref(false);
  const selected = ref<TendbsingleModel[]>([]);
  const currentData = ref<ColumnData['data']>();

  const getTableInstance = () => tableRef.value;

  const authorizeState = reactive({
    isShow: false,
    selected: [] as TendbsingleModel[],
  });

  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const searchSelectData = computed(() => [
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
      async: false,
    },
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
      multiple: true,
      async: false,
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
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
    },
    {
      name: t('模块'),
      id: 'db_module_id',
      multiple: true,
      children: searchAttrs.value.db_module_id,
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  // 设置用户个人表头信息
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBSINGLE_TABLE_SETTINGS, {
    checked: ['master_domain', 'status', 'cluster_stats', 'masters', 'db_module_id', 'major_version', 'region'],
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

  const fetchData = () => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value!.fetchData(params, { ...sortValue });
  };

  // 设置行样式
  const setRowClass = (row: TendbsingleModel) => {
    const classList = [row.isOffline ? 'is-offline' : ''];
    const newClass = row.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplySingle',
      query: {
        bizId: globalBizsStore.currentBizId,
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
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  /**
   * 表格选中
   */

  const handleSelection = (data: any, list: TendbsingleModel[]) => {
    selected.value = list;
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
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

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;
    }

    tr.is-offline {
      .vxe-cell {
        color: @disable-color;
      }
    }
  }
</style>
