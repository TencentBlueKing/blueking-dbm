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
  <div
    v-bkloading="{ loading: isLoading }"
    class="cluster-detail-dialog-mode">
    <template v-if="data">
      <DisplayBox
        cluster-detail-router-name="tendbClusterDetail"
        :data="data">
        <template #clb>
          <div
            v-if="data.isOnlineCLBMaster"
            class="ml-4">
            <ClusterEntryPanel
              clb-role="master_entry"
              :cluster-id="data.id"
              entry-type="clb"
              :panel-width="350"
              size="big" />
          </div>
        </template>
        <BkButton
          v-db-console="'mysql.haClusterList.authorize'"
          class="ml-4"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <AuthRouterLink
          v-db-console="'tendbCluster.clusterManage.webconsole'"
          action-id="tendbcluster_webconsole"
          class="ml-4"
          :permission="data.permission.tendbcluster_webconsole"
          :resource="data.id"
          target="_blank"
          :to="{
            name: 'SpiderWebconsole',
            query: {
              clusterId: data.id,
            },
          }">
          <BkButton
            :disabled="data.isOffline"
            size="small">
            Webconsole
          </BkButton>
        </AuthRouterLink>
        <BkButton
          v-db-console="'tendbCluster.clusterManage.exportData'"
          action-id="tendbcluster_dump_data"
          class="ml-4"
          :disabled="data.isOffline"
          :permission="data.permission.tendbcluster_dump_data"
          :resource="data.id"
          size="small"
          @click="handleShowDataExportSlider">
          {{ t('导出数据') }}
        </BkButton>
        <MoreActionExtend trigger="hover">
          <template #handler>
            <BkButton
              v-bk-tooltips="t('更多操作')"
              class="ml-4"
              size="small"
              style="padding: 0 6px">
              <DbIcon type="more" />
            </BkButton>
          </template>
          <BkDropdownItem
            v-bk-tooltips="{
              disabled: data.spider_mnt.length > 0,
              content: t('无运维节点'),
            }"
            v-db-console="'tendbCluster.clusterManage.removeMNTNode'">
            <div style="display: inline-block">
              <AuthButton
                action-id="tendbcluster_spider_mnt_destroy"
                :disabled="data.spider_mnt.length === 0 || data.isOffline"
                :permission="data.permission.tendbcluster_spider_mnt_destroy"
                :resource="data.id"
                text
                @click="handleRemoveMNT">
                {{ t('下架运维节点') }}
              </AuthButton>
            </div>
          </BkDropdownItem>
          <BkDropdownItem
            v-bk-tooltips="{
              disabled: data.spider_slave.length > 0,
              content: t('无只读集群'),
            }"
            v-db-console="'tendbCluster.clusterManage.removeReadonlyNode'">
            <div style="display: inline-block">
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
          </BkDropdownItem>
          <BkDropdownItem
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
                  handleAddClb({
                    details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id, spider_role: 'spider_master' },
                  })
                ">
                {{ t('启用 Spider Master 负载均衡（CLB）') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
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
                  handleAddClb({
                    details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id, spider_role: 'spider_slave' },
                  })
                ">
                {{ t('启用 Spider Slave 负载均衡（CLB）') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
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
          </BkDropdownItem>
          <BkDropdownItem
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
          <BkDropdownItem>
            <ClusterDomainDnsRelation :data="data" />
          </BkDropdownItem>
        </MoreActionExtend>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.TENDBCLUSTER">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :data="data"
            @refresh="fetchDetailData">
            <template #clbMaster>
              <ClbInfo
                :cluster-type="ClusterTypes.TENDBCLUSTER"
                :data="data"
                label="CLB（Master）"
                role="master_entry" />
            </template>
            <template #clbSlave>
              <ClbInfo
                :cluster-type="ClusterTypes.TENDBCLUSTER"
                :data="data"
                label="CLB（Slave）"
                role="slave_entry" />
            </template>
            <template #slaveDomain>
              <SlaveDomain
                :cluster-type="ClusterTypes.TENDBCLUSTER"
                :data="data.slaveEntryList" />
            </template>
            <template #moduleName>
              <ModuleNameInfo
                :cluster-type="ClusterTypes.TENDBCLUSTER"
                :data="data" />
            </template>
          </BaseInfo>
        </template>
      </ActionPanel>
      <ClusterAuthorize
        v-model="isAuthorizeShow"
        :account-type="AccountTypes.TENDBCLUSTER"
        :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
        :selected="[data]" />
      <ClusterExportData
        v-model:is-show="isShowDataExport"
        :data="data"
        :ticket-type="TicketTypes.TENDBCLUSTER_DUMP_DATA" />
    </template>
  </div>
</template>

<script setup lang="tsx">
  import { Checkbox } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterDetailModel from '@services/model/tendbcluster/tendbcluster-detail';
  import { getTendbclusterDetail, getTendbclusterPrimary } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import {
    ActionPanel,
    BaseInfo,
    BaseInfoField,
    DisplayBox,
    SlaveDomain,
  } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import { useAddClb, useBindOrUnbindClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import { messageWarn } from '@utils';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { ClbInfo, ModuleNameInfo } = BaseInfoField;

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

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

  const data = ref<TendbClusterDetailModel>();
  const isAuthorizeShow = ref(false);
  const isShowDataExport = ref(false);
  const removeMNTInstanceIds = ref<number[]>([]);
  const clusterPrimaryMap = shallowRef<Record<string, boolean>>({});

  const clusterRoleNodeGroup = computed(() => {
    /* eslint-disable perfectionist/sort-objects */
    return {
      'Spider Master': (data.value?.spider_master || []).map((item) => ({
        ...item,
        isPrimary: clusterPrimaryMap.value[item.ip],
      })),
      'Spider Slave': data.value?.spider_slave || [],
      [t('运维节点')]: data.value?.spider_mnt || [],
      RemoteDB: (data.value?.remote_db || []).map((item) => ({
        ...item,
        displayInstance: `${item.instance}(%_${item.shard_id})`,
      })),
      RemoteDR: (data.value?.remote_dr || []).map((item) => ({
        ...item,
        displayInstance: `${item.instance}(%_${item.shard_id})`,
      })),
    };
    /* eslint-enable perfectionist/sort-objects */
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getTendbclusterDetail, {
    manual: true,
    onSuccess(result: TendbClusterDetailModel) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBCLUSTER,
    {
      onSuccess: () => {
        fetchDetailData();
        emits('change');
      },
    },
  );

  useRequest(getTendbclusterPrimary, {
    defaultParams: [
      {
        cluster_ids: [props.clusterId],
      },
    ],
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

  watch(
    () => props.clusterId,
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchDetailData();
    },
    {
      immediate: true,
    },
  );

  const handleShowAuthorize = () => {
    isAuthorizeShow.value = true;
  };

  const handleShowDataExportSlider = () => {
    isShowDataExport.value = true;
  };

  // 下架只读集群
  const handleDestroySlave = (data: TendbClusterDetailModel) => {
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

  // 下架运维节点
  const handleRemoveMNT = (data: TendbClusterDetailModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('下架'),
      content: () => (
        <div>
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
        </div>
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
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
