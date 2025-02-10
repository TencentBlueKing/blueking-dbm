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
        :selected="selected"
        @success="handleBatchOperationSuccess" />
      <BkButton
        v-db-console="'mysql.haClusterList.importAuthorize'"
        class="ml-8"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'mysql.haClusterList.export'"
        :ids="selectedIds"
        type="tendbha" />
      <ClusterIpCopy
        v-db-console="'mysql.haClusterList.batchCopy'"
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
    <div class="table-wrapper">
      <DbTable
        ref="tableRef"
        :data-source="getTendbhaList"
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
        <IdColumn :cluster-type="ClusterTypes.TENDBHA" />
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('主访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchData" />
        <ClusterNameColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected"
          @refresh="fetchData" />
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.TENDBHA"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected" />
        <StatusColumn :cluster-type="ClusterTypes.TENDBHA" />
        <ClusterStatsColumn :cluster-type="ClusterTypes.TENDBHA" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="proxies"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Proxy"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="masters"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Master"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBHA"
          field="slaves"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Slave"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected">
          <template #nodeTag="{ data }">
            <BkTag
              v-if="data.is_stand_by"
              class="is-stand-by"
              size="small">
              Standby
            </BkTag>
          </template>
        </RoleColumn>
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBHA" />
        <CommonColumn :cluster-type="ClusterTypes.TENDBHA" />
        <BkTableColumn
          :fixed="isStretchLayoutOpen ? false : 'right'"
          :label="t('操作')"
          :min-width="220"
          :show-overflow="false">
          <template #default="{data}: {data: TendbhaModel}">
            <BkButton
              v-db-console="'mysql.haClusterList.authorize'"
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
            <AuthButton
              v-db-console="'mysql.haClusterList.exportData'"
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
            <MoreActionExtend v-db-console="'mysql.haClusterList.moreOperation'">
              <BkDropdownItem
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
              </BkDropdownItem>
              <BkDropdownItem
                v-if="data.isOnline"
                v-db-console="'mysql.haClusterList.disable'">
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
                v-db-console="'mysql.haClusterList.enable'">
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
              <BkDropdownItem v-db-console="'mysql.haClusterList.delete'">
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
    :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave']"
    :selected="authorizeState.selected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBHA" />
  <CreateSubscribeRuleSlider
    v-model="showCreateSubscribeRuleSlider"
    :selected-clusters="selectedClusterList"
    show-tab-panel />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="showDataExportSlider"
    :data="currentData"
    :ticket-type="TicketTypes.MYSQL_DUMP_DATA" />
</template>

<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { MySQLFunctions } from '@services/model/function-controller/functionController';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaList } from '@services/source/tendbha';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useFunController, useGlobalBizs } from '@stores';

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
  import SlaveDomainColumn from '@views/db-manage/common/cluster-table-column/SlaveDomainColumn.vue';
  import StatusColumn from '@views/db-manage/common/cluster-table-column/StatusColumn.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  interface ColumnData {
    cell: string;
    data: TendbhaModel;
  }

  const clusterId = defineModel<number>('clusterId');

  // 设置行样式
  const setRowClass = (row: TendbhaModel) => {
    const classList = [row.isOffline ? 'is-offline' : ''];
    const newClass = row.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const funControllerStore = useFunController();
  const { t } = useI18n();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
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
    searchType: ClusterTypes.TENDBHA,
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const isInit = ref(false);
  const showCreateSubscribeRuleSlider = ref(false);
  const showDataExportSlider = ref(false);
  const selectedClusterList = ref<ColumnData['data'][]>([]);
  const currentData = ref<ColumnData['data']>();

  const selected = ref<TendbhaModel[]>([]);
  /** 集群授权 */
  const authorizeState = reactive({
    isShow: false,
    selected: [] as TendbhaModel[],
  });

  const getTableInstance = () => tableRef.value;

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
      name: t('所属DB模块'),
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

  const isShowDumperEntry = computed(() => {
    const currentKey = `dumper_biz_${globalBizsStore.currentBizId}` as MySQLFunctions;
    return funControllerStore.funControllerData.mysql.children[currentKey];
  });

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBHA_TABLE_SETTINGS, {
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      'slave_domain',
      'proxies',
      'masters',
      'slaves',
      'db_module_id',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'bk_cloud_id',
    ],
    disabled: ['master_domain'],
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

  const fetchData = (loading?: boolean) => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value!.fetchData(params, { ...sortValue }, loading);
    isInit.value = false;
  };

  const handleSelection = (data: any, list: TendbhaModel[]) => {
    selected.value = list;
    selectedClusterList.value = list;
  };

  const handleShowAuthorize = (selected: TendbhaModel[] = []) => {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  };

  const handleShowCreateSubscribeRuleSlider = (data?: ColumnData['data']) => {
    if (data) {
      // 单个集群订阅
      selectedClusterList.value = [data];
    }
    showCreateSubscribeRuleSlider.value = true;
  };

  const handleShowDataExportSlider = (data: ColumnData['data']) => {
    currentData.value = data;
    showDataExportSlider.value = true;
  };

  const handleClearSelected = () => {
    selected.value = [];
    authorizeState.selected = [];
  };

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  };

  onMounted(() => {
    if (route.query.id && !clusterId.value) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .mysql-ha-cluster-list-page {
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

    tr.is-offline {
      .vxe-cell {
        color: @disable-color;
      }
    }

    .is-stand-by {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }
</style>
