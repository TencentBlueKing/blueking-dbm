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
      <AuthButton
        v-db-console="'redis.clusterManage.instanceApply'"
        action-id="redis_cluster_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'redis.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.REDIS"
        :selected="selected"
        @success="fetchData" />
      <DropdownExportExcel
        v-db-console="'redis.clusterManage.export'"
        :ids="selectedIds"
        type="redis" />
      <ClusterIpCopy
        v-db-console="'redis.clusterManage.batchCopy'"
        :selected="selected" />
      <TagSearch @search="handleTagSearch" />
      <DbSearchSelect
        class="operations-right"
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
            <ClusterEntryPanel
              v-if="data.isOnlineCLB"
              :cluster-id="data.id"
              entry-type="clb" />
            <ClusterEntryPanel
              v-if="data.isOnlinePolaris"
              :cluster-id="data.id"
              entry-type="polaris"
              :panel-width="418" />
          </template>
        </MasterDomainColumn>
        <ClusterNameColumn
          :cluster-type="ClusterTypes.REDIS"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :selected-list="selected"
          @refresh="fetchData" />
        <ClusterTagColumn
          :cluster-type="ClusterTypes.REDIS"
          @success="fetchData" />
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
        <BkTableColumn
          field="module_names"
          label="Modules"
          :width="150">
          <template #default="{ data }: { data: RedisModel }">
            <TagBlock :data="data.module_names" />
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
                  @click="handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, [data])">
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
                @click="handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, [data])">
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
                    @click="handleToToolbox(TicketTypes.REDIS_BACKUP, [data])">
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
                    @click="handleToToolbox(TicketTypes.REDIS_PURGE, [data])">
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
                      @click="handleSwitchClb(data)">
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

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TagSearch from '@components/tag-search/index.vue';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterNameColumn from '@views/db-manage/common/cluster-table-column/ClusterNameColumn.vue';
  import ClusterStatsColumn from '@views/db-manage/common/cluster-table-column/ClusterStatsColumn.vue';
  import ClusterTagColumn from '@views/db-manage/common/cluster-table-column/ClusterTagColumn.vue';
  import CommonColumn from '@views/db-manage/common/cluster-table-column/CommonColumn.vue';
  import IdColumn from '@views/db-manage/common/cluster-table-column/IdColumn.vue';
  import MasterDomainColumn from '@views/db-manage/common/cluster-table-column/MasterDomainColumn.vue';
  import RoleColumn from '@views/db-manage/common/cluster-table-column/RoleColumn.vue';
  import StatusColumn from '@views/db-manage/common/cluster-table-column/StatusColumn.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic, useRedisClusterListToToolbox, useSwitchClb } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterPassword from '@views/db-manage/redis/common/cluster-oprations/ClusterPassword.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import MasterSlaveRoleColumn from './components/MasterSlaveRoleColume.vue';

  interface Exposes {
    refresh: () => void;
  }

  const clusterId = defineModel<number>('clusterId');

  enum ClusterNodeKeys {
    PROXY = 'proxy',
    REDIS_MASTER = 'redis_master',
    REDIS_SLAVE = 'redis_slave',
  }

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.REDIS,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleToToolbox } = useRedisClusterListToToolbox();
  const { handleSwitchClb } = useSwitchClb(ClusterTypes.REDIS_CLUSTER);
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

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
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone', 'cluster_type'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(),
    searchType: ClusterTypes.REDIS,
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const selected = ref<RedisModel[]>([]);
  const tagSearchValue = ref<Record<string, any>>({});

  const getTableInstance = () => tableRef.value;

  /** 查看密码 */
  const passwordState = reactive({
    fetchParams: {
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: -1,
      db_type: DBTypes.REDIS,
      type: DBTypes.REDIS,
    },
    isShow: false,
  });

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
      children: searchAttrs.value.cluster_type,
      id: 'cluster_type',
      multiple: true,
      name: t('架构版本'),
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

  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      align: 'left',
      layout: ['total', 'limit', 'list'],
      small: true,
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
      'tag',
    ],
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

  const getRowClass = (data: RedisModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchData();
  };

  const fetchData = () => {
    const params = {
      cluster_type: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ].join(','),
      ...getSearchSelectorParams(searchValue.value),
      ...tagSearchValue.value,
      ...sortValue,
    };

    tableRef.value!.fetchData(params);
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
   * 域名指向 clb / 域名解绑 clb
   */
  const handleSwitchDNSBindCLB = (data: RedisModel) => {
    const isBind = data.dns_to_clb;
    const title = isBind ? t('确认恢复 DNS 域名指向？') : t('确认将 DNS 域名指向 CLB ?');
    const content = isBind ? t('DNS 域名恢复指向 Proxy') : t('业务不需要更换原域名也可实现负载均衡');
    const type = isBind ? TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB : TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB;
    InfoBox({
      content,
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            cluster_id: data.id,
          },
          ticket_type: type,
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
        });
      },
      title,
      width: 400,
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
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            cluster_id: data.id,
          },
          ticket_type: ticketType,
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
        });
      },
      title,
      type: 'warning',
    });
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });

  defineExpose<Exposes>({
    refresh: fetchData,
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
