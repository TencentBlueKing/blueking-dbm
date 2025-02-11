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
  <div class="es-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'es.clusterManage.instanceApply'"
        action-id="es_apply"
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        v-db-console="'es.clusterManage.export'"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="es" />
      <ClusterIpCopy
        v-db-console="'es.clusterManage.batchCopy'"
        :selected="selected" />
      <DbSearchSelect
        class="mb16"
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      :pagination-extra="paginationExtra"
      releate-url-query
      :row-class="getRowClass"
      :row-config="{
        useKey: true,
        keyField: 'id',
      }"
      :scroll-y="{ enabled: true, gt: 0 }"
      selectable
      :settings="tableSetting"
      :show-overflow="false"
      show-settings
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <IdColumn :cluster-type="ClusterTypes.ES" />
      <MasterDomainColumn
        :cluster-type="ClusterTypes.ES"
        field="master_domain"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('访问入口')"
        :selected-list="selected"
        @go-detail="handleToDetails"
        @refresh="fetchTableData" />
      <ClusterNameColumn
        :cluster-type="ClusterTypes.ES"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :selected-list="selected"
        @refresh="fetchTableData" />
      <StatusColumn :cluster-type="ClusterTypes.ES" />
      <ClusterStatsColumn :cluster-type="ClusterTypes.ES" />
      <RoleColumn
        :cluster-type="ClusterTypes.ES"
        field="es_master"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('Master节点')"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <RoleColumn
        :cluster-type="ClusterTypes.ES"
        field="es_client"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('Client节点')"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <RoleColumn
        :cluster-type="ClusterTypes.ES"
        field="es_datanode_hot"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('热节点')"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <RoleColumn
        :cluster-type="ClusterTypes.ES"
        field="es_datanode_cold"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :label="t('冷节点')"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <CommonColumn :cluster-type="ClusterTypes.ES" />
      <BkTableColumn
        :fixed="isStretchLayoutOpen ? false : 'right'"
        :label="t('操作')"
        :min-width="200"
        :show-overflow="false">
        <template #default="{data}: {data: EsModel}">
          <template v-if="data.isOffline">
            <AuthButton
              v-db-console="'es.clusterManage.enable'"
              action-id="es_enable_disable"
              class="mr-8"
              :disabled="data.isStarting"
              :permission="data.permission.es_enable_disable"
              :resource="data.id"
              text
              theme="primary"
              @click="handleEnableCluster([data])">
              {{ t('启用') }}
            </AuthButton>
          </template>
          <template v-else>
            <OperationBtnStatusTips
              v-db-console="'es.clusterManage.scaleUp'"
              :data="data">
              <AuthButton
                action-id="es_scale_up"
                class="mr8"
                :disabled="data.operationDisabled"
                :permission="data.permission.es_scale_up"
                :resource="data.id"
                text
                theme="primary"
                @click="handleShowExpandsion(data)">
                {{ t('扩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips
              v-db-console="'es.clusterManage.scaleDown'"
              :data="data">
              <AuthButton
                action-id="es_shrink"
                class="mr8"
                :disabled="data.operationDisabled"
                :permission="data.permission.es_shrink"
                :resource="data.id"
                text
                theme="primary"
                @click="handleShowShrink(data)">
                {{ t('缩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </template>
          <AuthButton
            v-db-console="'es.clusterManage.getAccess'"
            action-id="es_access_entry_view"
            class="mr-8"
            :disabled="data.isOffline"
            :permission="data.permission.es_access_entry_view"
            :resource="data.id"
            text
            theme="primary"
            @click="handleShowPassword(data)">
            {{ t('获取访问方式') }}
          </AuthButton>
          <MoreActionExtend>
            <BkDropdownItem
              v-if="data.isOnline"
              v-db-console="'es.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="es_enable_disable"
                  :disabled="Boolean(data.operationTicketId)"
                  :permission="data.permission.es_enable_disable"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
            <BkDropdownItem v-db-console="'es.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="es_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.es_destroy"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
            <BkDropdownItem v-db-console="'es.clusterManage.manage'">
              <a
                :href="data.access_url"
                style="color: #63656e"
                target="_blank">
                {{ t('管理') }}
              </a>
            </BkDropdownItem>
          </MoreActionExtend>
        </template>
      </BkTableColumn>
    </DbTable>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      background-color="#F5F7FA"
      class="es-manage-sideslider"
      :title="t('xx扩容【name】', { title: 'ES', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      background-color="#F5F7FA"
      class="es-manage-sideslider"
      :title="t('xx缩容【name】', { title: 'ES', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
        :node-list="[]"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      render-directive="if"
      :title="t('获取访问方式')"
      :width="500">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import EsModel from '@services/model/es/es';
  import { getEsList } from '@services/source/es';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterNameColumn from '@views/db-manage/common/cluster-table-column/ClusterNameColumn.vue';
  import ClusterStatsColumn from '@views/db-manage/common/cluster-table-column/ClusterStatsColumn.vue';
  import CommonColumn from '@views/db-manage/common/cluster-table-column/CommonColumn.vue';
  import IdColumn from '@views/db-manage/common/cluster-table-column/IdColumn.vue';
  import MasterDomainColumn from '@views/db-manage/common/cluster-table-column/MasterDomainColumn.vue';
  import RoleColumn from '@views/db-manage/common/cluster-table-column/RoleColumn.vue';
  import StatusColumn from '@views/db-manage/common/cluster-table-column/StatusColumn.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterExpansion from '@views/db-manage/elastic-search/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/elastic-search/common/shrink/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams, isRecentDays } from '@utils';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(ClusterTypes.ES, {
    onSuccess: () => fetchTableData(),
  });
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
    searchType: ClusterTypes.ES,
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchTableData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const serachData = computed(() => [
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
      name: t('创建人'),
      id: 'creator',
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
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  const dataSource = getEsList;
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);
  const selected = ref<EsModel[]>([]);
  const operationData = shallowRef<EsModel>();

  const getTableInstance = () => tableRef.value;

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  const getRowClass = (data: EsModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = isRecentDays(data.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.ES_TABLE_SETTINGS, {
    disabled: ['master_domain'],
    checked: [
      'status',
      'cluster_stats',
      'major_version',
      'region',
      'disaster_tolerance_level',
      'es_master',
      'es_client',
      'es_datanode_hot',
      'es_datanode_cold',
    ],
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

  const fetchTableData = (loading?: boolean) => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams, { ...sortValue }, loading);
    isInit.value = false;
  };

  const handleSelection = (data: any, list: EsModel[]) => {
    selected.value = list;
  };

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'EsApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpandsion = (data: EsModel) => {
    isShowExpandsion.value = true;
    operationData.value = data;
  };

  // 缩容
  const handleShowShrink = (data: EsModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  const handleShowPassword = (clusterData: EsModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less">
  .es-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

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
  }
</style>
