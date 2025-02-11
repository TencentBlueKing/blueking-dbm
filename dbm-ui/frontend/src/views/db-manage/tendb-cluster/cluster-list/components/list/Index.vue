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
  <div class="spider-manage-list-page">
    <div class="operations">
      <div class="mb-16">
        <AuthButton
          v-db-console="'tendbCluster.clusterManage.instanceApply'"
          action-id="tendbcluster_apply"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </AuthButton>
        <ClusterBatchOperation
          v-db-console="'tendbCluster.clusterManage.batchOperation'"
          class="ml-8"
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :selected="selected"
          @success="handleBatchOperationSuccess" />
        <span
          v-bk-tooltips="{
            disabled: hasData,
            content: t('请先创建实例'),
          }"
          v-db-console="'tendbCluster.clusterManage.importAuthorize'"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasData"
            @click="handleShowExcelAuthorize">
            {{ t('导入授权') }}
          </BkButton>
        </span>
        <DropdownExportExcel
          v-db-console="'tendbCluster.clusterManage.export'"
          :ids="selectedIds"
          type="spider" />
        <ClusterIpCopy
          v-db-console="'tendbCluster.clusterManage.batchCopy'"
          :selected="selected" />
      </div>
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
      :class="{
        'is-shrink-table': isStretchLayoutOpen,
      }">
      <DbTable
        ref="tableRef"
        :data-source="fetchData"
        :pagination-extra="paginationExtra"
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
        @selection="handleTableSelected"
        @setting-change="updateTableSettings">
        <IdColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
        <MasterDomainColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('主访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchTableData" />
        <ClusterNameColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected"
          @refresh="fetchTableData" />
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected" />
        <StatusColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
        <ClusterStatsColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
        <MasterSlaveRoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_master"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Spider Master"
          :search-ip="searchIp"
          :selected-list="selected">
          <template #nodeTag="{ data }">
            <BkTag
              v-if="clusterPrimaryMap[data.ip]"
              class="is-primary"
              size="small">
              Primary
            </BkTag>
          </template>
        </MasterSlaveRoleColumn>
        <MasterSlaveRoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_slave"
          :get-table-instance="getTableInstance"
          label="Spider Slave"
          :search-ip="searchIp"
          :selected-list="selected" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_mnt"
          :get-table-instance="getTableInstance"
          :label="t('运维节点')"
          :search-ip="searchIp"
          :selected-list="selected" />
        <RemoteRoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="remote_db"
          :get-table-instance="getTableInstance"
          label="RemoteDB"
          :search-ip="searchIp"
          :selected-list="selected" />
        <RemoteRoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="remote_dr"
          :get-table-instance="getTableInstance"
          label="RemoteDR"
          :search-ip="searchIp"
          :selected-list="selected" />
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
        <CommonColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
        <BkTableColumn
          :fixed="isStretchLayoutOpen ? false : 'right'"
          :label="t('操作')"
          :min-width="220"
          :show-overflow="false">
          <template #default="{data}: IColumn">
            <BkButton
              v-db-console="'mysql.haClusterList.authorize'"
              class="mr-8"
              :disabled="data.isOffline"
              text
              theme="primary"
              @click="() => handleShowAuthorize([data])">
              {{ t('授权') }}
            </BkButton>
            <AuthRouterLink
              v-db-console="'tendbCluster.clusterManage.webconsole'"
              action-id="tendbcluster_webconsole"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.tendbcluster_webconsole"
              :resource="data.id"
              target="_blank"
              :to="{
                name: 'SpiderWebconsole',
                query: {
                  clusterId: data.id,
                },
              }">
              Webconsole
            </AuthRouterLink>
            <AuthButton
              v-db-console="'tendbCluster.clusterManage.exportData'"
              action-id="tendbcluster_dump_data"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.tendbcluster_dump_data"
              :resource="data.id"
              text
              theme="primary"
              @click="() => handleShowDataExportSlider(data)">
              {{ t('导出数据') }}
            </AuthButton>
            <MoreActionExtend>
              <BkDropdownItem
                v-bk-tooltips="{
                  disabled: data.spider_mnt.length > 0,
                  content: t('无运维节点'),
                }"
                v-db-console="'tendbCluster.clusterManage.removeMNTNode'">
                <AuthButton
                  action-id="tendbcluster_spider_mnt_destroy"
                  :disabled="data.spider_mnt.length === 0 || data.isOffline"
                  :permission="data.permission.tendbcluster_spider_mnt_destroy"
                  :resource="data.id"
                  text
                  @click="handleRemoveMNT(data)">
                  {{ t('下架运维节点') }}
                </AuthButton>
              </BkDropdownItem>
              <BkDropdownItem
                v-bk-tooltips="{
                  disabled: data.spider_slave.length > 0,
                  content: t('无只读集群'),
                }"
                v-db-console="'tendbCluster.clusterManage.removeReadonlyNode'">
                <AuthButton
                  action-id="tendb_spider_slave_destroy"
                  :disabled="data.spider_slave.length === 0 || data.isOffline"
                  :permission="data.permission.tendb_spider_slave_destroy"
                  :resource="data.id"
                  text
                  @click="handleDestroySlave(data)">
                  {{ t('下架只读集群') }}
                </AuthButton>
              </BkDropdownItem>
              <BkDropdownItem
                v-if="data.isOnline"
                v-db-console="'tendbCluster.clusterManage.disable'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    action-id="tendbcluster_enable_disable"
                    :disabled="Boolean(data.operationTicketId)"
                    :permission="data.permission.tendbcluster_enable_disable"
                    :resource="data.id"
                    text
                    @click="handleDisableCluster([data])">
                    {{ t('禁用') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem
                v-if="data.isOffline"
                v-db-console="'tendbCluster.clusterManage.enable'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    action-id="tendbcluster_enable_disable"
                    :disabled="data.isStarting"
                    :permission="data.permission.tendbcluster_enable_disable"
                    :resource="data.id"
                    text
                    @click="handleEnableCluster([data])">
                    {{ t('启用') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'tendbCluster.clusterManage.delete'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    v-bk-tooltips="{
                      disabled: data.isOffline,
                      content: t('请先禁用集群'),
                    }"
                    action-id="tendbcluster_destroy"
                    :disabled="data.isOnline || Boolean(data.operationTicketId)"
                    :permission="data.permission.tendbcluster_destroy"
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
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
    :selected="selected"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    :ticket-type="TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES" />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="showDataExportSlider"
    :data="currentData"
    :ticket-type="TicketTypes.TENDBCLUSTER_DUMP_DATA" />
</template>

<script setup lang="tsx">
  import { Checkbox } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import {
    getTendbClusterList,
    getTendbclusterPrimary,
  } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue'
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue'
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

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
    messageWarn,
  } from '@utils';

  import MasterSlaveRoleColumn from './components/MasterSlaveRoleColume.vue';
  import RemoteRoleColumn from './components/RemoteRoleColumn.vue';

  interface IColumn {
    data: TendbClusterModel
  }

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBCLUSTER,
    {
      onSuccess: () => fetchTableData(),
    },
  );

  const {
    searchAttrs,
    searchValue,
    sortValue,
    isFilter,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBCLUSTER,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchTableData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const clusterId = defineModel<number>('clusterId');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const removeMNTInstanceIds = ref<number[]>([]);
  const excelAuthorizeShow = ref(false);
  const clusterAuthorizeShow = ref(false);
  const showDataExportSlider = ref(false)
  const currentData = ref<IColumn['data']>()
  const selected = ref<TendbClusterModel[]>([]);
  const clusterPrimaryMap = ref<Record<string, boolean>>({});

  const getTableInstance = () => tableRef.value

  const selectedIds = computed(() => selected.value.map(item => item.id));
  const tableDataList = computed(() => tableRef.value?.getData<TendbClusterModel>() || [])
  const hasData = computed(() => tableDataList.value.length > 0);

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

  const searchIp = computed<string[]>(() => {
    const ipObj = searchValue.value.find(item => item.id === 'ip');
    if (ipObj && ipObj.values) {
      return [ipObj.values[0].id];
    }
    return [];
  });

  const { run: getSpiderClusterPrimaryRun } = useRequest(getTendbclusterPrimary, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        clusterPrimaryMap.value = data.reduce<Record<string, boolean>>((acc, cur) => {
          const ip = cur.primary.split(':')[0];
          if (ip) {
            acc[ip] = true;
          }
          return acc;
        }, {});
      }
    },
  });

  const { runAsync: fetchData } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess(data) {
      const clusterIds = data.results.map(item => item.id);
      if (clusterIds.length > 0) {
        getSpiderClusterPrimaryRun({
          cluster_ids: clusterIds,
        });
      }
    },
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
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  // 设置行样式
  const setRowClass = (row: TendbClusterModel) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBCLUSTER_TABLE_SETTINGS, {
    checked: [
      'master_domain',
      'slave_domain',
      'status',
      'cluster_stats',
      'spider_master',
      'spider_slave',
      'spider_mnt',
      'remote_db',
      'remote_dr',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'spec_name',
      'bk_cloud_id',
    ],
    disabled: ['master_domain'],
  });

  let isInitData = true;
  const fetchTableData = () => {
    tableRef.value?.fetchData({
      ...getSearchSelectorParams(searchValue.value),
    }, { ...sortValue }, isInitData);
    isInitData = false;

    return Promise.resolve([]);
  };

  // 查看集群详情
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 下架运维节点
  const handleRemoveMNT = (data: TendbClusterModel) => {
    InfoBox({
      width: 480,
      title: t('确认下架运维节点'),
      content: () => (
        <>
          <p>{t('下架后将无法再访问_请谨慎操作')}</p>
          <div style="text-align: left; padding: 0 24px;">
            <p class="pt-12" style="font-size: 12px;">{t('请勾选要下架的运维节点')}</p>
            <Checkbox.Group class="mnt-checkbox-group" style="flex-wrap: wrap;" v-model={removeMNTInstanceIds.value}>
              {
                data.spider_mnt.map(item => <Checkbox label={item.bk_instance_id}>{item.instance}</Checkbox>)
              }
            </Checkbox.Group>
          </div>
        </>
      ),
      confirmText: t('下架'),
      cancelText: t('取消'),
      onConfirm: () => {
        if (removeMNTInstanceIds.value.length === 0) {
          messageWarn(t('请勾选要下架的运维节点'));
          return false;
        }
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'TENDBCLUSTER_SPIDER_MNT_DESTROY',
          details: {
            is_safe: true,
            infos: [
              {
                cluster_id: data.id,
                spider_ip_list: data.spider_mnt
                  .filter(item => removeMNTInstanceIds.value.includes(item.bk_instance_id))
                  .map(item => ({
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
              },
            ],
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            removeMNTInstanceIds.value = [];
            return true;
          })
          .catch(() => false);
      },
      onCancel: () => {
        removeMNTInstanceIds.value = [];
      },
    });
  };

  // 下架只读集群
  const handleDestroySlave = (data: TendbClusterModel) => {
    InfoBox({
      type: 'warning',
      title: t('确认下架只读集群'),
      content: t('下架后将无法访问只读集群'),
      onConfirm: () => createTicket({
        bk_biz_id: currentBizId,
        ticket_type: 'TENDBCLUSTER_SPIDER_SLAVE_DESTROY',
        details: {
          is_safe: true,
          cluster_ids: [data.id],
        },
      })
        .then((res) => {
          ticketMessage(res.id);
        })
    });
  };

  // 申请实例
  const handleApply = () => {
    router.push({
      name: 'spiderApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleTableSelected = (data: unknown, list: TendbClusterModel[]) => {
    selected.value = list;
  };

  const handleShowAuthorize = (list: TendbClusterModel[] = []) => {
    clusterAuthorizeShow.value = true;
    selected.value = list;
  };

  const handleClearSelected = () => {
    tableRef.value!.clearSelected();
    selected.value = [];
  };

  const handleShowDataExportSlider = (data: IColumn['data']) => {
    currentData.value = data
    showDataExportSlider.value = true;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchTableData();
  }

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less">
  .spider-manage-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operations {
      display: flex;
      margin-bottom: 16px;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
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

    .is-primary {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }

  .mnt-checkbox-group {
    flex-wrap: wrap;

    .bk-checkbox {
      margin-top: 8px;
      margin-left: 0;
      flex: 0 0 50%;
    }
  }

  .struct-cluster-source-popover {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 12px;
    padding: 2px 0;

    .title {
      font-size: 12px;
      font-weight: 700;
      color: #313238;
    }

    .item-row {
      display: flex;
      width: 100%;
      align-items: center;
      overflow: hidden;

      .label {
        width: 72px;
        text-align: right;
      }

      .content {
        flex: 1;
        overflow: hidden;
        cursor: pointer;
      }
    }
  }
</style>
