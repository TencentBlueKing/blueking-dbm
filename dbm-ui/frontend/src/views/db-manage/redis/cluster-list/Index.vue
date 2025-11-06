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
        :selected="selectedList"
        @success="fetchData" />
      <DropdownExportExcel
        v-db-console="'redis.clusterManage.export'"
        :ids="selectedIdList"
        type="redis" />
      <ClusterIpCopy
        v-db-console="'redis.clusterManage.batchCopy'"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.REDIS"
      :data-source="dataSource"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.REDIS">
          <template #default="{ data }: { data: RedisModel }">
            <div v-db-console="'redis.clusterManage.extractKey'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <span
                  v-bk-tooltips="{
                    content: t('暂不支持跨管控区域提取Key'),
                    disabled: data.bk_cloud_id === 0,
                  }">
                  <AuthButton
                    action-id="redis_keys_extract"
                    :disabled="data.isOffline || data.bk_cloud_id !== 0"
                    :permission="data.permission.redis_keys_extract"
                    :resource="data.id"
                    text
                    @click="handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, [data])">
                    {{ t('提取Key') }}
                  </AuthButton>
                </span>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'redis.clusterManage.deleteKey'">
              <OperationBtnStatusTips
                v-bk-tooltips="{
                  content: t('暂不支持跨管控区域删除Key'),
                  disabled: data.bk_cloud_id === 0,
                }"
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="redis_keys_delete"
                  :disabled="data.isOffline || data.bk_cloud_id !== 0"
                  :permission="data.permission.redis_keys_delete"
                  :resource="data.id"
                  text
                  @click="handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, [data])">
                  {{ t('删除Key') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div>
              <AuthRouterLink
                action-id="redis_webconsole"
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
            </div>
            <div v-db-console="'redis.clusterManage.backup'">
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
            </div>
            <div v-db-console="'redis.clusterManage.dbClear'">
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
            </div>
            <div v-db-console="'redis.clusterManage.getAccess'">
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
            </div>
            <div v-db-console="'redis.clusterManage.queryAccessSource'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="redis_source_access_view"
                  :disabled="data.isOffline"
                  :permission="data.permission.redis_source_access_view"
                  :resource="data.id"
                  style="width: 100%; height: 32px"
                  text
                  @click="handleGoQueryAccessSourcePage(data.master_domain)">
                  {{ t('查询访问来源') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <!-- <FunController
                controller-id="redis_nameservice"
                module-id="addons"> -->
            <div
              v-if="!data.isOnlineCLB"
              v-db-console="'common.clb'">
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
                  @click="() => handleAddClb({ details: { cluster_id: data.id } })">
                  {{ t('启用CLB') }}
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
                  action-id="redis_plugin_dns_bind_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.redis_plugin_dns_bind_clb"
                  :resource="data.id"
                  style="width: 100%; height: 32px"
                  text
                  @click="() => handleBindOrUnbindClb({ details: { cluster_id: data.id } }, data.dns_to_clb)">
                  {{ data.dns_to_clb ? t('恢复DNS域名指向') : t('DNS域名指向CLB') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlinePolaris"
              v-db-console="'common.polaris'">
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
                  @click="() => handleAddPolaris({ details: { cluster_id: data.id } })">
                  {{ t('启用北极星') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <!-- </FunController> -->
            <div
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
            </div>
            <div
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
            </div>
            <div v-db-console="'redis.clusterManage.delete'">
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
            </div>
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.REDIS"
          :db-type="DBTypes.REDIS"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('访问入口')"
          :selected-list="selectedList"
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
            <div
              v-if="data.isOnlinePolaris"
              class="ml-4">
              <ClusterEntryPanel
                :cluster-id="data.id"
                entry-type="polaris"
                :panel-width="418" />
            </div>
            <ClusterLoad
              :cluster-type="ClusterTypes.REDIS"
              :domain="data.master_domain"
              size="small" />
          </template>
        </MasterDomainColumn>
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="proxy"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Proxy"
          :min-width="260"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="redis_master"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Master"
          :min-width="260"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #default="{ data }: { data: RedisModel['redis_slave'][number] }">
            {{ data.ip }}:{{ data.port }}
            <template v-if="data.seg_range">({{ data.seg_range }})</template>
          </template>
        </RoleColumn>
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS"
          field="redis_slave"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Slave"
          :min-width="260"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #default="{ data }: { data: RedisModel['redis_slave'][number] }">
            {{ data.ip }}:{{ data.port }}
            <template v-if="data.seg_range">({{ data.seg_range }})</template>
          </template>
        </RoleColumn>
      </template>
      <template #clusterTypeName>
        <TableColumn
          col-key="cluster_type_name"
          :min-width="150"
          :title="t('架构版本')">
          <template #default="{ row }: { row: RedisModel }">
            {{ row.cluster_type_name || '--' }}
          </template>
        </TableColumn>
      </template>
      <template #moduleNames>
        <TableColumn
          col-key="module_names"
          title="Modules"
          :width="150">
          <template #default="{ row }: { row: RedisModel }">
            <TagBlock :data="row.module_names" />
          </template>
        </TableColumn>
      </template>
    </ClusterTable>
  </div>
  <!-- 查看密码 -->
  <ClusterPassword
    v-model:is-show="passwordState.isShow"
    :fetch-params="passwordState.fetchParams" />

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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterLoad from '@views/db-manage/common/cluster-load/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import {
    useAddClb,
    useAddPolaris,
    useBindOrUnbindClb,
    useOperateClusterBasic,
    useRedisClusterListToToolbox,
  } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/redis/common/cluster-detail/Index.vue';
  import ClusterPassword from '@views/db-manage/redis/common/cluster-operations/ClusterPassword.vue';

  const dataSource = (params: ServiceParameters<typeof getRedisList>) =>
    getRedisList({
      ...params,
      cluster_type: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ].join(','),
    });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch([
    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    ClusterTypes.PREDIXY_REDIS_CLUSTER,
  ]);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.REDIS,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleToToolbox } = useRedisClusterListToToolbox();
  const { handleAddClb } = useAddClb<{ cluster_id: number }>(ClusterTypes.REDIS_CLUSTER);
  const { handleAddPolaris } = useAddPolaris<{ cluster_id: number }>(ClusterTypes.REDIS_CLUSTER);
  const { handleBindOrUnbindClb } = useBindOrUnbindClb<{ cluster_id: number }>(ClusterTypes.REDIS_CLUSTER);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('redisClusterDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<RedisModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');

  const getTableInstance = () => tableRef.value;

  /** 查看密码 */
  const passwordState = reactive({
    fetchParams: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: -1,
      db_type: DBTypes.REDIS,
      type: DBTypes.REDIS,
    },
    isShow: false,
  });

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.REDIS_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...searchValue.value,
    });
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyRedis',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleShowPassword = (id: number) => {
    passwordState.isShow = true;
    passwordState.fetchParams.cluster_id = id;
  };

  const handleGoQueryAccessSourcePage = (domain: string) => {
    const url = router.resolve({
      name: 'RedisQueryAccessSource',
      query: {
        domain,
      },
    });
    window.open(url.href);
  };

  const handleQuickSearchChange = () => {
    fetchData();
    tableRef.value!.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchData();
  };
</script>
<style lang="less">
  .redis-cluster-list-page {
    .operation-box {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
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
