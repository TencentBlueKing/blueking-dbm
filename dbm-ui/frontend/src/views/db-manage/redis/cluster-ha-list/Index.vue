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
  <div class="redis-cluster-ha-list-page">
    <div class="operation-box">
      <AuthButton
        action-id="redis_cluster_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'redis.haClusterManage.batchOperation'"
        :cluster-type="ClusterTypes.REDIS_INSTANCE"
        :selected="selectedList"
        @success="fetchData" />
      <DropdownExportExcel
        :ids="selectedIdList"
        type="redis" />
      <ClusterIpCopy
        v-db-console="'redis.haClusterManage.batchCopy'"
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
      :cluster-type="ClusterTypes.REDIS_INSTANCE"
      :data-source="dataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.REDIS_INSTANCE">
          <template #default="{ data }: { data: RedisModel }">
            <div v-db-console="'redis.haClusterManage.extractKey'">
              <OperationBtnStatusTips
                v-bk-tooltips="{
                  content: t('暂不支持跨管控区域提取Key'),
                  disabled: data.bk_cloud_id === undefined,
                }"
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="redis_keys_extract"
                  class="mr-8"
                  :disabled="data.isOffline"
                  :permission="data.permission.redis_keys_extract"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, [data])">
                  {{ t('提取Key') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'redis.haClusterManage.deleteKey'">
              <OperationBtnStatusTips
                v-bk-tooltips="{
                  content: t('暂不支持跨管控区域删除Key'),
                  disabled: data.bk_cloud_id === undefined,
                }"
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="redis_keys_delete"
                  class="mr-8"
                  :disabled="data.isOffline"
                  :permission="data.permission.redis_keys_delete"
                  :resource="data.id"
                  text
                  theme="primary"
                  @click="handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, [data])">
                  {{ t('删除Key') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div>
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
            </div>
            <div v-db-console="'redis.haClusterManage.backup'">
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
            <div v-db-console="'redis.haClusterManage.dbClear'">
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
            <div v-db-console="'redis.haClusterManage.getAccess'">
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
            <div v-db-console="'redis.haClusterManage.queryAccessSource'">
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
            <div
              v-if="data.isOnline"
              v-db-console="'redis.haClusterManage.disable'">
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
              v-db-console="'redis.haClusterManage.enable'">
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
            <div v-db-console="'redis.haClusterManage.delete'">
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
            <ClusterDomainDnsRelation :data="data" />
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.REDIS_INSTANCE"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('主访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchData">
          <template #append="{ data }">
            <ClusterLoad
              :cluster-type="ClusterTypes.REDIS_INSTANCE"
              :domain="data.master_domain"
              size="small" />
          </template>
        </MasterDomainColumn>
      </template>
      <template #slaveDomain>
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.REDIS_INSTANCE"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS_INSTANCE"
          field="redis_master"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Master"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.REDIS_INSTANCE"
          field="redis_slave"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Slave"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
      </template>
      <template #moduleNames>
        <TableColumn
          col-key="module_names"
          :min-width="150"
          title="Modules">
          <template #default="{ row }: { row: RedisModel }">
            <TagBlock :data="row.module_names" />
          </template>
        </TableColumn>
      </template>
    </ClusterTable>
    <!-- 查看密码 -->
    <ClusterPassword
      v-model:is-show="passwordState.isShow"
      :fetch-params="passwordState.fetchParams"
      :show-clb="false" />
    <TableDetailDialog
      v-model="isShowDetail"
      :default-offset-left="300"
      @close="handleDetailClose">
      <ClusterDetail
        v-if="clusterId"
        :cluster-id="clusterId" />
    </TableDetailDialog>
  </div>
</template>
<script setup lang="tsx">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';

  import { useClusterQuickSearch, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterLoad from '@views/db-manage/common/cluster-load/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
    SlaveDomainColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic, useRedisClusterListToToolbox } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/redis/common/cluster-ha-detail/Index.vue';
  import ClusterPassword from '@views/db-manage/redis/common/cluster-operations/ClusterPassword.vue';

  const dataSource = (params: ServiceParameters<typeof getRedisList>) =>
    getRedisList({
      ...params,
      cluster_type: ClusterTypes.REDIS_INSTANCE,
    });
  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.REDIS);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.REDIS_INSTANCE,
    {
      onSuccess: () => fetchData(),
    },
  );
  const { handleToToolbox } = useRedisClusterListToToolbox();

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('redisClusterHaDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<RedisModel>();

  const disableSelectMethod = (data: RedisModel) => {
    if (data.operations?.length > 0) {
      const operationData = data.operations[0];
      return ([TicketTypes.REDIS_INSTANCE_DESTROY, TicketTypes.REDIS_INSTANCE_CLOSE] as string[]).includes(
        operationData.ticket_type,
      );
    }

    return false;
  };

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
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

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.REDIS_HA_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  const fetchData = () => {
    tableRef.value!.fetchData(searchValue.value);
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyRedisHa',
      query: {
        bizId: globalBizsStore.currentBizId,
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
  .redis-cluster-ha-list-page {
    .operation-box {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;
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

  .redis-manage-infobox {
    .bk-modal-body {
      .bk-modal-header {
        .bk-dialog-header {
          .bk-dialog-title {
            margin-top: 18px;
            margin-bottom: 16px;
          }
        }
      }

      .bk-modal-footer {
        height: 80px;
      }
    }
  }
</style>
