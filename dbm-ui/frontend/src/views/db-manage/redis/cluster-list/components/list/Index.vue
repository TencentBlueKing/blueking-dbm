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
  <div class="redis-cluster-list-page">
    <div class="operation-box">
      <div>
        <AuthButton
          v-db-console="'redis.clusterManage.instanceApply'"
          action-id="redis_cluster_apply"
          class="mb-16"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </AuthButton>
        <ClusterBatchOperation
          v-db-console="'redis.clusterManage.batchOperation'"
          class="ml-8"
          :cluster-type="ClusterTypes.REDIS"
          :selected="selected"
          @success="handleBatchOperationSuccess" />
        <DropdownExportExcel
          v-db-console="'redis.clusterManage.export'"
          :ids="selectedIds"
          type="redis" />
        <ClusterIpCopy
          v-db-console="'redis.clusterManage.batchCopy'"
          :selected="selected" />
      </div>
      <DbSearchSelect
        class="operations-right mb-16"
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
        :data-source="getRedisList"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
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
        <IdColumn :cluster-type="ClusterTypes.REDIS" />
        <MasterDomainColumn
          :cluster-type="ClusterTypes.REDIS"
          :db-type="DBTypes.REDIS"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchData">
          <template #append="{ data }">
            <EntryPanel
              v-if="data.isOnlineCLB"
              :cluster-id="data.id"
              entry-type="clb">
              <MiniTag
                content="CLB"
                ext-cls="redis-manage-clb-minitag" />
            </EntryPanel>
            <EntryPanel
              v-if="data.isOnlinePolaris"
              :cluster-id="data.id"
              entry-type="polaris"
              :panel-width="418">
              <MiniTag
                content="北极星"
                ext-cls="redis-manage-polary-minitag" />
            </EntryPanel>
          </template>
        </MasterDomainColumn>
        <ClusterNameColumn
          :cluster-type="ClusterTypes.REDIS"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected"
          @refresh="fetchData" />
        <StatusColumn :cluster-type="ClusterTypes.REDIS" />
        <ClusterStatsColumn :cluster-type="ClusterTypes.REDIS" />
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="proxy"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Proxy"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <MasterSlaveRoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="redis_master"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Master"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <MasterSlaveRoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="redis_slave"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Slave"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected" />
        <BkTableColumn
          field="cluster_type_name"
          :label="t('架构版本')"
          :min-width="150">
          <template #default="{ data }: { data: RedisModel }">
            {{ data.cluster_type_name || '--' }}
          </template>
        </BkTableColumn>
        <CommonColumn :cluster-type="ClusterTypes.REDIS" />
        <BkTableColumn
          :fixed="isStretchLayoutOpen ? false : 'right'"
          :label="t('操作')"
          :min-width="240"
          :show-overflow="false">
          <template #default="{data}: {data: RedisModel}">
            <OperationBtnStatusTips
              v-db-console="'redis.clusterManage.extractKey'"
              :data="data"
              :disabled="!data.isOffline">
              <span
                v-bk-tooltips="{
                  content: t('暂不支持跨管控区域提取Key'),
                  disabled: data.bk_cloud_id === 0,
                }">
                <AuthButton
                  action-id="redis_keys_extract"
                  class="mr-8"
                  :disabled="data.isOffline || data.bk_cloud_id !== 0"
                  :permission="data.permission.redis_keys_extract"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleShowExtract([data])">
                  {{ t('提取Key') }}
                </AuthButton>
              </span>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips
              v-bk-tooltips="{
                content: t('暂不支持跨管控区域删除Key'),
                disabled: data.bk_cloud_id === 0,
              }"
              v-db-console="'redis.clusterManage.deleteKey'"
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="redis_keys_delete"
                class="mr-8"
                :disabled="data.isOffline || data.bk_cloud_id !== 0"
                :permission="data.permission.redis_keys_delete"
                :resource="data.id"
                text
                theme="primary"
                @click="handlShowDeleteKeys([data])">
                {{ t('删除Key') }}
              </AuthButton>
            </OperationBtnStatusTips>
            <AuthRouterLink
              action-id="redis_webconsole"
              class="mr-8"
              :disabled="data.isOffline"
              :permission="data.permission.redis_webconsole"
              :resource="data.id"
              target="_blank"
              :to="{
                name: 'RedisWebconsole',
                query: {
                  clusterId: data.id,
                },
              }">
              Webconsole
            </AuthRouterLink>
            <MoreActionExtend v-db-console="'redis.clusterManage.moreOperation'">
              <BkDropdownItem v-db-console="'redis.clusterManage.backup'">
                <OperationBtnStatusTips
                  :data="data"
                  :disabled="!data.isOffline">
                  <AuthButton
                    action-id="redis_backup"
                    :disabled="data.isOffline"
                    :permission="data.permission.redis_backup"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
                    text
                    @click="handleShowBackup([data])">
                    {{ t('备份') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'redis.clusterManage.dbClear'">
                <OperationBtnStatusTips
                  :data="data"
                  :disabled="!data.isOffline">
                  <AuthButton
                    action-id="redis_purge"
                    :disabled="data.isOffline"
                    :permission="data.permission.redis_purge"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
                    text
                    @click="handleShowPurge([data])">
                    {{ t('清档') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'redis.clusterManage.getAccess'">
                <OperationBtnStatusTips
                  :data="data"
                  :disabled="!data.isOffline">
                  <AuthButton
                    action-id="redis_access_entry_view"
                    :disabled="data.isOffline"
                    :permission="data.permission.redis_access_entry_view"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
                    text
                    @click="handleShowPassword(data.id)">
                    {{ t('获取访问方式') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <FunController
                controller-id="redis_nameservice"
                module-id="addons">
                <BkDropdownItem v-db-console="'redis.clusterManage.enableCLB'">
                  <OperationBtnStatusTips
                    :data="data"
                    :disabled="!data.isOffline">
                    <AuthButton
                      action-id="redis_plugin_create_clb"
                      :disabled="data.isOffline"
                      :permission="data.permission.redis_plugin_create_clb"
                      :resource="data.id"
                      style="width: 100%; height: 32px"
                      text
                      @click="handleSwitchCLB(data)">
                      {{ data.isOnlineCLB ? t('禁用CLB') : t('启用CLB') }}
                    </AuthButton>
                  </OperationBtnStatusTips>
                </BkDropdownItem>

                <BkDropdownItem v-db-console="'redis.clusterManage.DNSDomainToCLB'">
                  <OperationBtnStatusTips
                    :data="data"
                    :disabled="!data.isOffline">
                    <AuthButton
                      action-id="redis_plugin_dns_bind_clb"
                      :disabled="data.isOffline"
                      :permission="data.permission.redis_plugin_dns_bind_clb"
                      :resource="data.id"
                      style="width: 100%; height: 32px"
                      text
                      @click="handleSwitchDNSBindCLB(data)">
                      {{ data.dns_to_clb ? t('恢复DNS域名指向') : t('DNS域名指向CLB') }}
                    </AuthButton>
                  </OperationBtnStatusTips>
                </BkDropdownItem>

                <BkDropdownItem v-db-console="'redis.clusterManage.enablePolaris'">
                  <OperationBtnStatusTips
                    :data="data"
                    :disabled="!data.isOffline">
                    <AuthButton
                      action-id="redis_plugin_create_polaris"
                      :disabled="data.isOffline"
                      :permission="data.permission.redis_plugin_create_polaris"
                      :resource="data.id"
                      style="width: 100%; height: 32px"
                      text
                      @click="handleSwitchPolaris(data)">
                      {{ data.isOnlinePolaris ? t('禁用北极星') : t('启用北极星') }}
                    </AuthButton>
                  </OperationBtnStatusTips>
                </BkDropdownItem>
              </FunController>
              <BkDropdownItem
                v-if="data.isOnline"
                v-db-console="'redis.clusterManage.disable'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    action-id="redis_open_close"
                    :disabled="Boolean(data.operationTicketId)"
                    :permission="data.permission.redis_open_close"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
                    text
                    @click="handleDisableCluster([data])">
                    {{ t('禁用') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem
                v-if="data.isOffline"
                v-db-console="'redis.clusterManage.enable'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    action-id="redis_open_close"
                    :disabled="data.isStarting"
                    :permission="data.permission.redis_open_close"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
                    text
                    @click="handleEnableCluster([data])">
                    {{ t('启用') }}
                  </AuthButton>
                </OperationBtnStatusTips>
              </BkDropdownItem>
              <BkDropdownItem v-db-console="'redis.clusterManage.delete'">
                <OperationBtnStatusTips :data="data">
                  <AuthButton
                    v-bk-tooltips="{
                      disabled: data.isOffline,
                      content: t('请先禁用集群'),
                    }"
                    action-id="redis_destroy"
                    :disabled="data.isOnline || Boolean(data.operationTicketId)"
                    :permission="data.permission.redis_destroy"
                    :resource="data.id"
                    style="width: 100%; height: 32px"
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
  <!-- 查看密码 -->
  <ClusterPassword
    v-model:is-show="passwordState.isShow"
    :fetch-params="passwordState.fetchParams" />
  <!-- 提取 keys -->
  <ExtractKeys
    v-model:is-show="extractState.isShow"
    :data="extractState.data" />
  <!-- 删除 keys -->
  <DeleteKeys
    v-model:is-show="deleteKeyState.isShow"
    :data="deleteKeyState.data" />
  <!-- 备份 -->
  <RedisBackup
    v-model:is-show="backupState.isShow"
    :data="backupState.data" />
  <!-- 清档 -->
  <RedisPurge
    v-model:is-show="purgeState.isShow"
    :data="purgeState.data" />
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketCloneInfo,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
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
  import { useShowBackup } from '@views/db-manage/common/redis-backup/hooks/useShowBackup';
  import RedisBackup from '@views/db-manage/common/redis-backup/Index.vue';
  import { useShowDeleteKeys } from '@views/db-manage/common/redis-delete-keys/hooks/useShowDeleteKeys';
  import DeleteKeys from '@views/db-manage/common/redis-delete-keys/Index.vue';
  import { useShowExtractKeys } from '@views/db-manage/common/redis-extract-keys/hooks/useShowExtractKeys';
  import ExtractKeys from '@views/db-manage/common/redis-extract-keys/Index.vue';
  import { useShowPurge } from '@views/db-manage/common/redis-purge/hooks/useShowPurge';
  import RedisPurge from '@views/db-manage/common/redis-purge/Index.vue';
  import ClusterPassword from '@views/db-manage/redis/common/cluster-oprations/ClusterPassword.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import EntryPanel from './components/EntryPanel.vue';
  import MasterSlaveRoleColumn from './components/MasterSlaveRoleColume.vue';

  enum ClusterNodeKeys {
    PROXY = 'proxy',
    REDIS_MASTER = 'redis_master',
    REDIS_SLAVE = 'redis_slave',
  }

  const clusterId = defineModel<number>('clusterId');

  let isInit = true;

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const { state: extractState, handleShow: handleShowExtract } = useShowExtractKeys();
  const { state: deleteKeyState, handleShow: handlShowDeleteKeys } = useShowDeleteKeys();
  const { state: backupState, handleShow: handleShowBackup } = useShowBackup();
  const { state: purgeState, handleShow: handleShowPurge } = useShowPurge();
  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.REDIS,
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
    searchType: ClusterTypes.REDIS,
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone', 'cluster_type'],
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  // 提取Key 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_KEYS_EXTRACT,
    onSuccess(cloneData) {
      extractState.isShow = true;
      extractState.data = cloneData;
      window.changeConfirm = true;
    },
  });

  // 删除Key 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_KEYS_DELETE,
    onSuccess(cloneData) {
      deleteKeyState.isShow = true;
      deleteKeyState.data = cloneData;
      window.changeConfirm = true;
    },
  });

  // 集群备份单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_BACKUP,
    onSuccess(cloneData) {
      backupState.isShow = true;
      backupState.data = cloneData;
      window.changeConfirm = true;
    },
  });

  // 清档单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_PURGE,
    onSuccess(cloneData) {
      purgeState.isShow = true;
      purgeState.data = cloneData;
      window.changeConfirm = true;
    },
  });

  // const disabledOperations: string[] = [TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE];

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const selected = ref<RedisModel[]>([]);

  const getTableInstance = () => tableRef.value;

  /** 查看密码 */
  const passwordState = reactive({
    isShow: false,
    fetchParams: {
      cluster_id: -1,
      bk_biz_id: globalBizsStore.currentBizId,
      db_type: DBTypes.REDIS,
      type: DBTypes.REDIS,
    },
  });

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
      name: t('架构版本'),
      id: 'cluster_type',
      multiple: true,
      children: searchAttrs.value.cluster_type,
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
  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.REDIS_TABLE_SETTINGS, {
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      ClusterNodeKeys.PROXY,
      ClusterNodeKeys.REDIS_MASTER,
      ClusterNodeKeys.REDIS_SLAVE,
      'cluster_type_name',
      'major_version',
      'module_names',
      'disaster_tolerance_level',
      'region',
      'spec_name',
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

  const getRowClass = (data: RedisModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  const fetchData = (loading?: boolean) => {
    const params = {
      cluster_type: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ].join(','),
      ...getSearchSelectorParams(searchValue.value),
    };

    tableRef.value!.fetchData(
      params,
      {
        ...sortValue,
      },
      loading,
    );
    isInit = false;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyRedis',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleSelection = (idList: any, list: RedisModel[]) => {
    selected.value = list;
  };

  /**
   * 查看集群详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleShowPassword = (id: number) => {
    passwordState.isShow = true;
    passwordState.fetchParams.cluster_id = id;
  };

  /**
   * 集群 CLB 启用/禁用
   */
  const handleSwitchCLB = (data: RedisModel) => {
    const ticketType = data.isOnlineCLB ? TicketTypes.REDIS_PLUGIN_DELETE_CLB : TicketTypes.REDIS_PLUGIN_CREATE_CLB;

    const title = ticketType === TicketTypes.REDIS_PLUGIN_CREATE_CLB ? t('确定启用CLB？') : t('确定禁用CLB？');

    InfoBox({
      title,
      content: t('启用 CLB 之后，该集群可以通过 CLB 来访问'),
      width: 400,
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: ticketType,
          details: {
            cluster_id: data.id,
          },
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
        });
      },
    });
  };

  /**
   * 域名指向 clb / 域名解绑 clb
   */
  const handleSwitchDNSBindCLB = (data: RedisModel) => {
    const isBind = data.dns_to_clb;
    const title = isBind ? t('确认恢复 DNS 域名指向？') : t('确认将 DNS 域名指向 CLB ?');
    const content = isBind ? t('DNS 域名恢复指向 Proxy') : t('业务不需要更换原域名也可实现负载均衡');
    const type = isBind ? TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB : TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB;
    InfoBox({
      title,
      content,
      width: 400,
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: type,
          details: {
            cluster_id: data.id,
          },
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
        });
      },
    });
  };

  /**
   * 集群 北极星启用/禁用
   */
  const handleSwitchPolaris = (data: RedisModel) => {
    const ticketType = data.isOnlinePolaris
      ? TicketTypes.REDIS_PLUGIN_DELETE_POLARIS
      : TicketTypes.REDIS_PLUGIN_CREATE_POLARIS;

    const title = ticketType === TicketTypes.REDIS_PLUGIN_CREATE_POLARIS ? t('确定启用北极星') : t('确定禁用北极星');
    InfoBox({
      type: 'warning',
      title,
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: ticketType,
          details: {
            cluster_id: data.id,
          },
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
        });
      },
    });
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

  .redis-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;

    .operation-box {
      display: flex;
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

    .redis-manage-clb-minitag {
      color: #8e3aff;
      cursor: pointer;
      background-color: #f2edff;

      &:hover {
        color: #8e3aff;
        background-color: #e3d9fe;
      }
    }

    .redis-manage-polary-minitag {
      color: #3a84ff;
      cursor: pointer;
      background-color: #edf4ff;

      &:hover {
        color: #3a84ff;
        background-color: #e1ecff;
      }
    }
  }
</style>
