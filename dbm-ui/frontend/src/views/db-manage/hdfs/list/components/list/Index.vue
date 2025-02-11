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
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        v-db-console="'hdfs.clusterManage.export'"
        :ids="selectedIds"
        type="hdfs" />
      <ClusterIpCopy
        v-db-console="'hdfs.clusterManage.batchCopy'"
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
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
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
        <IdColumn :cluster-type="ClusterTypes.HDFS" />
        <MasterDomainColumn
          :cluster-type="ClusterTypes.HDFS"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :label="t('访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchTableData" />
        <ClusterNameColumn
          :cluster-type="ClusterTypes.HDFS"
          :get-table-instance="getTableInstance"
          :selected-list="selected"
          @refresh="fetchTableData" />
        <StatusColumn :cluster-type="ClusterTypes.HDFS" />
        <ClusterStatsColumn :cluster-type="ClusterTypes.HDFS" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_namenode"
          :get-table-instance="getTableInstance"
          label="NameNode"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_zookeeper"
          :get-table-instance="getTableInstance"
          label="Zookeeper"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_journalnode"
          :get-table-instance="getTableInstance"
          label="Journalnode"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.HDFS"
          field="hdfs_datanode"
          :get-table-instance="getTableInstance"
          label="DataNode"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <CommonColumn :cluster-type="ClusterTypes.HDFS" />
        <BkTableColumn
          :fixed="isStretchLayoutOpen ? false : 'right'"
          :label="t('操作')"
          :min-width="200"
          :show-overflow="false">
          <template #default="{data}: {data: HdfsModel}">
            <template v-if="data.isOffline">
              <OperationBtnStatusTips
                v-db-console="'hdfs.clusterManage.enable'"
                :data="data">
                <AuthButton
                  v-db-console="'hdfs.clusterManage.enable'"
                  action-id="hdfs_enable_disable"
                  class="mr-8"
                  :disabled="data.isStarting"
                  :permission="data.permission.hdfs_enable_disable"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </template>
            <template v-else>
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-db-console="'hdfs.clusterManage.scaleUp'"
                  action-id="hdfs_scale_up"
                  class="mr-8"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.hdfs_scale_up"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleShowExpansion(data)">
                  {{ t('扩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-db-console="'hdfs.clusterManage.scaleDown'"
                  action-id="hdfs_shrink"
                  class="mr-8"
                  :disabled="data.operationDisabled"
                  :permission="data.permission.hdfs_shrink"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleShowShrink(data)">
                  {{ t('缩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </template>
            <AuthButton
              v-db-console="'hdfs.clusterManage.getAccess'"
              action-id="hdfs_access_entry_view"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.hdfs_access_entry_view"
              :resource="data.id"
              text
              theme="primary"
              @click="handleShowPassword(data)">
              {{ t('获取访问方式') }}
            </AuthButton>
            <MoreActionExtend>
              <BkDropdownItem v-db-console="'hdfs.clusterManage.viewAccessConfiguration'">
                <AuthButton
                  action-id="hdfs_view"
                  :disabled="data.isOffline"
                  :permission="data.permission.hdfs_view"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleShowSettings(data)">
                  {{ t('查看访问配置') }}
                </AuthButton>
              </BkDropdownItem>
              <BkDropdownItem
                v-if="data.isOnline"
                v-db-console="'hdfs.clusterManage.disable'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    action-id="hdfs_enable_disable"
                    :disabled="Boolean(data.operationTicketId)"
                    :permission="data.permission.hdfs_enable_disable"
                    :resource="data.id"
                    text
                    theme="primary"
                    @click="handleDisableCluster([data])">
                    {{ t('禁用') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'hdfs.clusterManage.delete'">
                <OperationBtnStatusTips
                  v-db-console="'hdfs.clusterManage.delete'"
                  :data="data">
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
                    theme="primary"
                    @click="handleDeleteCluster([data])">
                    {{ t('删除') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'hdfs.clusterManage.manage'">
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
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      background-color="#F5F7FA"
      class="hdfs-manage-sideslider"
      quick-close
      :title="t('xx扩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      background-color="#F5F7FA"
      class="hdfs-manage-sideslider"
      quick-close
      :title="t('xx缩容【name】', { title: 'HDFS', name: operationData?.cluster_name })"
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
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import HdfsModel from '@services/model/hdfs/hdfs';
  import { getHdfsList } from '@services/source/hdfs';
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
  import ClusterExpansion from '@views/db-manage/hdfs/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/hdfs/common/shrink/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import ClusterSettings from './components/ClusterSettings.vue';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const { t } = useI18n();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(ClusterTypes.HDFS, {
    onSuccess: () => fetchTableData(),
  });
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { currentBizId } = useGlobalBizs();
  const router = useRouter();

  const {
    searchAttrs,
    searchValue,
    sortValue,
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.HDFS,
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchTableData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const dataSource = getHdfsList;

  const tableRef = ref<InstanceType<typeof DbTable>>();

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isShowSettings = ref(false);
  const isInit = ref(true);
  const operationData = shallowRef<HdfsModel>();
  const selected = ref<HdfsModel[]>([]);

  const getTableInstance = () => tableRef.value;

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

  const getRowClass = (data: HdfsModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.HDFS_TABLE_SETTINGS, {
    disabled: ['master_domain'],
    checked: [
      'status',
      'cluster_stats',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'hdfs_namenode',
      'hdfs_zookeeper',
      'hdfs_journalnode',
      'hdfs_datanode',
    ],
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

  const handleSelection = (data: any, list: HdfsModel[]) => {
    selected.value = list;
  };

  // 集群提单
  const handleGoApply = () => {
    router.push({
      name: 'HdfsApply',
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

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less">
  .hdfs-list-page {
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
