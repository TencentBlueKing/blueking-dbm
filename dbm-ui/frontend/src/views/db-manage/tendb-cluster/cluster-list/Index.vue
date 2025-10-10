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
      <AuthButton
        v-db-console="'tendbCluster.clusterManage.instanceApply'"
        action-id="tendbcluster_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'tendbCluster.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.TENDBCLUSTER"
        :selected="selectedList"
        @success="fetchTableData" />
      <span
        v-bk-tooltips="{
          disabled: hasData,
          content: t('请先创建实例'),
        }"
        v-db-console="'tendbCluster.clusterManage.importAuthorize'"
        class="inline-block">
        <BkButton
          :disabled="!hasData"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
      </span>
      <DropdownExportExcel
        v-db-console="'tendbCluster.clusterManage.export'"
        :ids="selectedIdList"
        type="spider" />
      <ClusterIpCopy
        v-db-console="'tendbCluster.clusterManage.batchCopy'"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.TENDBCLUSTER"
      :data-source="fetchData"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.TENDBCLUSTER">
          <template #default="{ data }: { data: TendbClusterModel }">
            <div v-db-console="'mysql.haClusterList.authorize'">
              <BkButton
                :disabled="data.isOffline"
                text
                @click="() => handleShowAuthorize([data])">
                {{ t('授权') }}
              </BkButton>
            </div>
            <div v-db-console="'tendbCluster.clusterManage.webconsole'">
              <AuthRouterLink
                action-id="tendbcluster_webconsole"
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
            </div>
            <div v-db-console="'tendbCluster.clusterManage.exportData'">
              <AuthButton
                action-id="tendbcluster_dump_data"
                :disabled="data.isOffline"
                :permission="data.permission.tendbcluster_dump_data"
                :resource="data.id"
                text
                @click="() => handleShowDataExportSlider(data)">
                {{ t('导出数据') }}
              </AuthButton>
            </div>
            <div
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
            </div>
            <div
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
            </div>
            <div
              v-if="!data.isOnlineCLBMaster"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="tendbcluster_add_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.tendbcluster_add_clb"
                  :resource="data.id"
                  text
                  @click="
                    () =>
                      handleAddClb({
                        details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id, spider_role: 'spider_master' },
                      })
                  ">
                  {{ t('启用 Spider Master 负载均衡（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlineCLBSlave"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="tendbcluster_add_clb"
                  :disabled="data.isOffline"
                  :permission="data.permission.tendbcluster_add_clb"
                  :resource="data.id"
                  text
                  @click="
                    () =>
                      handleAddClb({
                        details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id, spider_role: 'spider_slave' },
                      })
                  ">
                  {{ t('启用 Spider Slave 负载均衡（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnlineCLBMaster"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="tendbcluster_clb_bind_domain"
                  :disabled="data.isOffline"
                  :permission="data.permission.tendbcluster_clb_bind_domain"
                  :resource="data.id"
                  text
                  @click="
                    () =>
                      handleBindOrUnbindClb(
                        {
                          details: {
                            cluster_id: data.id,
                            bk_cloud_id: data.bk_cloud_id,
                            spider_role: 'spider_master',
                          },
                        },
                        data.dns_to_clb,
                      )
                  ">
                  {{ data.dns_to_clb ? t('恢复主域名直连 Spider Master') : t('配置主域名指向负载均衡器（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOnlineCLBSlave"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="tendbcluster_clb_bind_domain"
                  :disabled="data.isOffline"
                  :permission="data.permission.tendbcluster_clb_bind_domain"
                  :resource="data.id"
                  text
                  @click="
                    () =>
                      handleBindOrUnbindClb(
                        {
                          details: {
                            cluster_id: data.id,
                            bk_cloud_id: data.bk_cloud_id,
                            spider_role: 'spider_slave',
                          },
                        },
                        data.dns_to_clb,
                      )
                  ">
                  {{ data.dns_to_clb ? t('恢复从域名直连 Spider Slave') : t('配置从域名指向负载均衡器（CLB）') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
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
            </div>
            <div
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
            </div>
            <div v-db-console="'tendbCluster.clusterManage.delete'">
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
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('主访问入口')"
          :selected-list="selectedList"
          @go-detail="handleToDetails"
          @refresh="fetchTableData">
          <template #append="{ data }">
            <div
              v-if="data.isOnlineCLBMaster"
              class="ml-4">
              <ClusterEntryPanel
                clb-role="master_entry"
                :cluster-id="data.id"
                entry-type="clb"
                :panel-width="350" />
            </div>
          </template>
        </MasterDomainColumn>
      </template>
      <template #slaveDomain>
        <SlaveDomainColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
          <template #append="{ data }">
            <div
              v-if="data.isOnlineCLBSlave"
              class="ml-4">
              <ClusterEntryPanel
                clb-role="slave_entry"
                :cluster-id="data.id"
                entry-type="clb"
                :panel-width="350" />
            </div>
          </template>
        </SlaveDomainColumn>
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_master"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Spider Master"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #nodeTag="{ data }">
            <BkTag
              v-if="clusterPrimaryMap[data.ip]"
              class="is-primary"
              size="small">
              Primary
            </BkTag>
          </template>
        </RoleColumn>
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_slave"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="Spider Slave"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="spider_mnt"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :label="t('运维节点')"
          :selected-list="selectedList"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="remote_db"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="RemoteDB"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #default="{ data }: { data: TendbClusterModel['remote_db'][number] }">
            {{ data.ip }}:{{ data.port }}(%_{{ data.shard_id }})
          </template>
        </RoleColumn>
        <RoleColumn
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          field="remote_dr"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          label="RemoteDR"
          :selected-list="selectedList"
          @go-detail="handleToDetails">
          <template #default="{ data }: { data: TendbClusterModel['remote_dr'][number] }">
            {{ data.ip }}:{{ data.port }}(%_{{ data.shard_id }})
          </template>
        </RoleColumn>
      </template>
      <template #moduleNames>
        <ModuleNameColumn :cluster-type="ClusterTypes.TENDBCLUSTER" />
      </template>
    </ClusterTable>
  </div>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
    :selected="selectedList"
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
  import { Checkbox } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbClusterList, getTendbclusterPrimary } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { useClusterQuickSearch, useTableSettings, useTicketMessage } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

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
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/tendb-cluster/common/cluster-detail/Index.vue';

  import { messageWarn } from '@utils';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const { isSearching, quickSearchData, searchValue } = useClusterQuickSearch(ClusterTypes.TENDBCLUSTER);
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBCLUSTER,
    {
      onSuccess: () => fetchTableData(),
    },
  );

  const { handleAddClb } = useAddClb<{
    bk_cloud_id: number;
    cluster_id: number;
    spider_role: string; // spider_master / spider_slave'
  }>(ClusterTypes.TENDBCLUSTER);
  const { handleBindOrUnbindClb } = useBindOrUnbindClb<{
    bk_cloud_id: number;
    cluster_id: number;
    spider_role: string; // spider_master / spider_slave'
  }>(ClusterTypes.TENDBCLUSTER);

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('tendbClusterDetail');
  const { handleSelection, selectedIdList, selectedList } = useClusterTableSelect<TendbClusterModel>();

  const tableRef = useTemplateRef<ComponentExposed<typeof ClusterTable>>('clusterTable');
  const removeMNTInstanceIds = ref<number[]>([]);
  const excelAuthorizeShow = ref(false);
  const clusterAuthorizeShow = ref(false);
  const showDataExportSlider = ref(false);
  const currentData = ref<TendbClusterModel>();
  const clusterPrimaryMap = ref<Record<string, boolean>>({});

  const getTableInstance = () => tableRef.value;

  const tableDataList = computed(() => tableRef.value?.getData<TendbClusterModel>() || []);
  const hasData = computed(() => tableDataList.value.length > 0);

  const { run: getSpiderClusterPrimaryRun } = useRequest(getTendbclusterPrimary, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        clusterPrimaryMap.value = data.reduce<Record<string, boolean>>((acc, cur) => {
          const ip = cur.primary.split(':')[0];
          if (ip) {
            Object.assign(acc, {
              [ip]: true,
            });
          }
          return acc;
        }, {});
      }
    },
  });

  const { runAsync: fetchData } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess(data) {
      const clusterIds = data.results.map((item) => item.id);
      if (clusterIds.length > 0) {
        getSpiderClusterPrimaryRun({
          cluster_ids: clusterIds,
        });
      }
    },
  });

  const fetchTableData = () => {
    tableRef.value?.fetchData(searchValue.value);
  };

  watch(searchValue, () => {
    setTimeout(() => {
      tableRef.value?.clearSelected();

      fetchTableData();
    });
  });

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.TENDBCLUSTER_TABLE_SETTINGS, {
    disabled: ['master_domain'],
  });

  // 下架运维节点
  const handleRemoveMNT = (data: TendbClusterModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('下架'),
      content: () => (
        <>
          <p>{t('下架后将无法再访问_请谨慎操作')}</p>
          <div style='text-align: left; padding: 0 24px;'>
            <p
              class='pt-12'
              style='font-size: 12px;'>
              {t('请勾选要下架的运维节点')}
            </p>
            <Checkbox.Group
              v-model={removeMNTInstanceIds.value}
              class='mnt-checkbox-group'
              style='flex-wrap: wrap;'>
              {data.spider_mnt.map((item) => (
                <Checkbox label={item.bk_instance_id}>{item.instance}</Checkbox>
              ))}
            </Checkbox.Group>
          </div>
        </>
      ),
      onCancel: () => {
        removeMNTInstanceIds.value = [];
      },
      onConfirm: () => {
        if (removeMNTInstanceIds.value.length === 0) {
          messageWarn(t('请勾选要下架的运维节点'));
          return false;
        }
        return createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            infos: [
              {
                cluster_id: data.id,
                old_nodes: {
                  spider_ip_list: data.spider_mnt
                    .filter((item) => removeMNTInstanceIds.value.includes(item.bk_instance_id))
                    .map((item) => ({
                      bk_cloud_id: item.bk_cloud_id,
                      bk_host_id: item.bk_host_id,
                      ip: item.ip,
                    })),
                },
              },
            ],
            is_safe: true,
          },
          ticket_type: TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY,
        })
          .then((res) => {
            ticketMessage(res.id);
            removeMNTInstanceIds.value = [];
            return true;
          })
          .catch(() => false);
      },
      title: t('确认下架运维节点'),
      width: 480,
    });
  };

  // 下架只读集群
  const handleDestroySlave = (data: TendbClusterModel) => {
    InfoBox({
      content: t('下架后将无法访问只读集群'),
      onConfirm: () =>
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            cluster_ids: [data.id],
            is_safe: true,
          },
          ticket_type: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY,
        }).then((res) => {
          ticketMessage(res.id);
        }),
      title: t('确认下架只读集群'),
      type: 'warning',
    });
  };

  // 申请实例
  const handleApply = () => {
    router.push({
      name: 'spiderApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  const handleShowAuthorize = (list: TendbClusterModel[] = []) => {
    clusterAuthorizeShow.value = true;
    selectedList.value = list;
  };

  const handleClearSelected = () => {
    tableRef.value!.clearSelected();
    selectedList.value = [];
  };

  const handleShowDataExportSlider = (data: TendbClusterModel) => {
    currentData.value = data;
    showDataExportSlider.value = true;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchTableData();
  };
</script>
<style lang="less">
  .spider-manage-list-page {
    .operations {
      display: flex;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 8px;
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
