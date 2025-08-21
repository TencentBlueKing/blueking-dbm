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
        class="ml-8"
        :ids="selectedIds"
        type="tendbha" />
      <ClusterIpCopy
        v-db-console="'mysql.haClusterList.batchCopy'"
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
        :cluster-type="ClusterTypes.TENDBHA"
        :data-source="getTendbhaList"
        :settings="settings"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings">
        <template #operation>
          <OperationColumn :cluster-type="ClusterTypes.TENDBHA">
            <template #default="{ data }">
              <div v-db-console="'mysql.haClusterList.authorize'">
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
            field="master_domain"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            :label="t('主访问入口')"
            :selected-list="selected"
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
            :is-filter="isFilter"
            :selected-list="selected" />
        </template>
        <template #role>
          <RoleColumn
            :cluster-type="ClusterTypes.TENDBHA"
            field="proxies"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            label="Proxy"
            :search-ip="batchSearchIpInatanceList"
            :selected-list="selected"
            @go-detail="handleToDetails" />
          <RoleColumn
            :cluster-type="ClusterTypes.TENDBHA"
            field="masters"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            label="Master"
            :search-ip="batchSearchIpInatanceList"
            :selected-list="selected"
            @go-detail="handleToDetails" />
          <RoleColumn
            :cluster-type="ClusterTypes.TENDBHA"
            field="slaves"
            :get-table-instance="getTableInstance"
            :is-filter="isFilter"
            label="Slave"
            :search-ip="batchSearchIpInatanceList"
            :selected-list="selected"
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

  import type { MySQLFunctions } from '@services/model/function-controller/functionController';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaList } from '@services/source/tendbha';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { useFunController } from '@stores';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

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
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/mysql/common/ha-cluster-detail/Index.vue';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  const route = useRoute();
  const router = useRouter();
  const funControllerStore = useFunController();
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
    searchType: ClusterTypes.TENDBHA,
  });

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('tendbHaDetail');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const isInit = ref(false);
  const showCreateSubscribeRuleSlider = ref(false);
  const showDataExportSlider = ref(false);
  const selectedClusterList = ref<TendbhaModel[]>([]);
  const currentData = ref<TendbhaModel>();
  const tagSearchValue = ref<Record<string, any>>({});
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
      name: t('所属DB模块'),
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

  const isShowDumperEntry = computed(() => {
    const currentKey = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as MySQLFunctions;
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

  const handleSelection = (data: any, list: TendbhaModel[]) => {
    selected.value = list;
    selectedClusterList.value = list;
  };

  const handleShowAuthorize = (selected: TendbhaModel[] = []) => {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  };

  const handleShowCreateSubscribeRuleSlider = (data?: TendbhaModel) => {
    if (data) {
      // 单个集群订阅
      selectedClusterList.value = [data];
    }
    showCreateSubscribeRuleSlider.value = true;
  };

  const handleShowDataExportSlider = (data: TendbhaModel) => {
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
