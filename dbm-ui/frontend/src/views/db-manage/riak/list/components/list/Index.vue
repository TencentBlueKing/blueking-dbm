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
  <div class="riak-cluster-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'riak.clusterManage.instanceApply'"
        action-id="riak_cluster_apply"
        theme="primary"
        @click="toApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        v-db-console="'riak.clusterManage.export'"
        :ids="selectedIds"
        type="riak" />
      <ClusterIpCopy
        v-db-console="'riak.clusterManage.batchCopy'"
        :selected="selected" />
      <DbSearchSelect
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        @change="handleSearchValueChange" />
      <BkDatePicker
        v-model="deployTime"
        append-to-body
        clearable
        :placeholder="t('请选择xx', [t('部署时间')])"
        type="daterange"
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="riak-list-table"
      :data-source="getRiakList"
      :row-class="setRowClass"
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
      <IdColumn :cluster-type="ClusterTypes.RIAK" />
      <MasterDomainColumn
        :cluster-type="ClusterTypes.RIAK"
        field="master_domain"
        :get-table-instance="getTableInstance"
        :label="t('主访问入口')"
        :selected-list="selected"
        @go-detail="handleToDetail"
        @refresh="fetchData" />
      <ClusterNameColumn
        :cluster-type="ClusterTypes.RIAK"
        :get-table-instance="getTableInstance"
        :selected-list="selected"
        @refresh="fetchData" />
      <StatusColumn :cluster-type="ClusterTypes.RIAK" />
      <ClusterStatsColumn :cluster-type="ClusterTypes.RIAK" />
      <RoleColumn
        :cluster-type="ClusterTypes.RIAK"
        field="riak_node"
        :get-table-instance="getTableInstance"
        :label="t('节点')"
        :search-ip="batchSearchIpInatanceList"
        :selected-list="selected" />
      <CommonColumn :cluster-type="ClusterTypes.RIAK" />
      <BkTableColumn
        :fixed="isStretchLayoutOpen ? false : 'right'"
        :label="t('操作')"
        :min-width="200"
        :show-overflow="false">
        <template #default="{data}: {data: RiakModel}">
          <OperationBtnStatusTips
            v-db-console="'riak.clusterManage.addNodes'"
            :data="data">
            <AuthButton
              action-id="riak_cluster_scale_in"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.riak_cluster_scale_in"
              :resource="data.id"
              text
              theme="primary"
              @click="handleAddNodes(data)">
              {{ t('添加节点') }}
            </AuthButton>
          </OperationBtnStatusTips>
          <OperationBtnStatusTips
            v-db-console="'riak.clusterManage.deleteNodes'"
            :data="data">
            <AuthButton
              action-id="riak_cluster_scale_out"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.riak_cluster_scale_out"
              :resource="data.id"
              text
              theme="primary"
              @click="handleDeleteNodes(data)">
              {{ t('删除节点') }}
            </AuthButton>
          </OperationBtnStatusTips>
          <OperationBtnStatusTips
            v-db-console="'riak.clusterManage.disable'"
            :data="data">
            <AuthButton
              action-id="riak_enable_disable"
              class="mr-8"
              :disabled="data.isOffline || Boolean(data.operationTicketId)"
              :permission="data.permission.riak_enable_disable"
              :resource="data.id"
              text
              theme="primary"
              @click="handleDisableCluster([data])">
              {{ t('禁用') }}
            </AuthButton>
          </OperationBtnStatusTips>
          <MoreActionExtend>
            <BkDropdownItem v-db-console="'riak.clusterManage.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="riak_enable_disable"
                  :disabled="data.isOnline || data.isStarting"
                  :permission="data.permission.riak_enable_disable"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
            <BkDropdownItem v-db-console="'riak.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="riak_cluster_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.riak_cluster_destroy"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </BkDropdownItem>
          </MoreActionExtend>
        </template>
      </BkTableColumn>
    </DbTable>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="addNodeShow"
      quick-close
      :title="t('添加节点【xx】', [detailData.cluster_name])"
      :width="960">
      <AddNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="deleteNodeShow"
      :title="t('删除节点【xx】', [detailData.cluster_name])"
      :width="960">
      <DeleteNodes
        :data="detailData"
        @submit-success="fetchData" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RiakModel from '@services/model/riak/riak';
  import { getRiakList } from '@services/source/riak';
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

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import AddNodes from '../components/AddNodes.vue';
  import DeleteNodes from '../components/DeleteNodes.vue';

  interface Emits {
    (e: 'detailOpenChange', data: boolean): void;
  }

  interface Expose {
    freshData: () => void;
  }

  const emits = defineEmits<Emits>();
  const clusterId = defineModel<number>('clusterId');

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(ClusterTypes.RIAK, {
    onSuccess: () => fetchData(),
  });
  const {
    searchAttrs,
    searchValue,
    sortValue,
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.RIAK,
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const serachData = computed(
    () =>
      [
        {
          name: t('集群名称'),
          id: 'name',
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
          name: t('创建人'),
          id: 'creator',
        },
        {
          name: t('模块'),
          id: 'db_module_id',
          multiple: true,
          children: searchAttrs.value.db_module_id,
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
      ] as ISearchItem[],
  );

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const deployTime = ref<[string, string]>(['', '']);
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const detailData = ref<RiakModel>();
  const selected = ref<RiakModel[]>([]);

  const getTableInstance = () => tableRef.value;

  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.RIAK_TABLE_SETTINGS, {
    checked: [
      'cluster_name',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'bk_cloud_id',
      'db_module_id',
      'status',
      'cluster_stats',
      'riak_node',
    ],
    disabled: ['master_domain'],
  });

  watch(isStretchLayoutOpen, (newVal) => {
    emits('detailOpenChange', newVal);
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

  const setRowClass = (row: RiakModel) => {
    const classList = [];

    if (row.isNew) {
      classList.push('is-new');
    }
    if (!row.isOnline) {
      classList.push('is-offline');
    }
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }

    return classList.join(' ');
  };

  const toApply = () => {
    router.push({
      name: 'RiakApply',
      query: {
        bizId: currentBizId,
      },
    });
  };

  const handleSelection = (key: unknown, list: RiakModel[]) => {
    selected.value = list;
  };

  const handleToDetail = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleAddNodes = (data: RiakModel) => {
    detailData.value = data;
    addNodeShow.value = true;
  };

  const handleDeleteNodes = (data: RiakModel) => {
    detailData.value = data;
    deleteNodeShow.value = true;
  };

  const fetchData = (
    otherParamas: {
      status?: string;
    } = {},
  ) => {
    const params = {
      ...otherParamas,
      ...getSearchSelectorParams(searchValue.value),
    };
    const [startTime, endTime] = deployTime.value;
    if (startTime && endTime) {
      Object.assign(params, {
        start_time: dayjs(startTime).format('YYYY-MM-DD'),
        end_time: dayjs(endTime).format('YYYY-MM-DD '),
      });
    }

    tableRef.value!.fetchData({ ...params }, sortValue);
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetail(Number(route.query.id));
    }
  });

  defineExpose<Expose>({
    freshData() {
      fetchData();
    },
  });
</script>
<style lang="less">
  .riak-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }

      .bk-date-picker {
        width: 300px;
        margin-left: 8px;
      }
    }

    tr {
      &.is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      &.is-offline {
        .vxe-cell {
          color: #c4c6cc !important;
        }
      }
    }
  }

  .info-box-cluster-name {
    color: #313238;
  }
</style>
