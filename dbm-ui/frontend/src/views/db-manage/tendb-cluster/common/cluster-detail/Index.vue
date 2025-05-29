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
      <DisplayBox :data="data">
        <BkButton
          v-db-console="'mysql.haClusterList.authorize'"
          class="ml-8"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <AuthButton
          v-db-console="'tendbCluster.clusterManage.webconsole'"
          action-id="tendbcluster_webconsole"
          class="ml-8"
          :disabled="data.isOffline"
          :permission="data.permission.tendbcluster_webconsole"
          :resource="data.id"
          size="small"
          @click="handleGoWebconsole">
          Webconsole
        </AuthButton>
        <BkButton
          v-db-console="'tendbCluster.clusterManage.exportData'"
          action-id="tendbcluster_dump_data"
          class="ml-8"
          :disabled="data.isOffline"
          :permission="data.permission.tendbcluster_dump_data"
          :resource="data.id"
          size="small"
          @click="handleShowDataExportSlider">
          {{ t('导出数据') }}
        </BkButton>
        <BkDropdown placement="bottom-start">
          <BkButton
            v-bk-tooltips="t('复制')"
            class="ml-8"
            size="small"
            style="padding: 0 6px">
            <DbIcon type="copy-2" />
          </BkButton>
          <template #content>
            <BkDropdownItem @click="handleCopyClusterMasterDomainAndLink">
              {{ t('集群域名 + 集群链接') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyLink">{{ t('集群链接') }}</BkDropdownItem>
          </template>
        </BkDropdown>
        <MoreActionExtend trigger="hover">
          <template #handler>
            <BkButton
              v-bk-tooltips="t('更多操作')"
              class="ml-8"
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
        <RouterLink
          v-if="!isDetailPage"
          style="margin-left: auto"
          target="_blank"
          :to="{
            name: 'tendbClusterDetail',
            params: {
              clusterId,
            },
          }">
          <DbIcon
            class="mr-4"
            type="link" />
          {{ t('新窗口打开') }}
        </RouterLink>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.TENDBCLUSTER">
        <template #infoContent>
          <BaseInfo :data="data" />
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbclusterDetail } from '@services/source/tendbcluster';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ActionPanel from '@views/db-manage/common/cluster-details/ActionPanel.vue';
  import DisplayBox from '@views/db-manage/common/cluster-details/DisplayBox.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import { execCopy, getSelfDomain } from '@utils';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const isDetailPage = 'tendbClusterDetail' === route.name;

  const data = ref<TendbClusterModel>();

  /** 集群授权 */
  const isAuthorizeShow = ref(false);
  const isShowDataExport = ref(false);
  const isShowCreateSubscribeRule = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    /* eslint-disable perfectionist/sort-objects */
    return {
      'Spider Master': data.value?.spider_master || [],
      'Spider Slave': data.value?.spider_slave || [],
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
    onSuccess(result: TendbClusterModel) {
      data.value = result;
    },
  });

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBCLUSTER,
    {
      onSuccess: () => {
        fetchClusterDetail({
          id: props.clusterId,
        });
        emits('change');
      },
    },
  );

  watch(
    () => props.clusterId,
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchClusterDetail({
        id: props.clusterId,
      });
    },
    {
      immediate: true,
    },
  );

  const handleShowAuthorize = () => {
    isAuthorizeShow.value = true;
  };

  const handleGoWebconsole = () => {
    const { href } = router.resolve({
      name: 'tendbClusterDetail',
      query: {
        clusterId: props.clusterId,
      },
    });
    window.open(href);
  };

  const handleShowDataExportSlider = () => {
    isShowDataExport.value = true;
  };

  const handleDestroySlave = () => {
    console.log('handleDestroySlave');
  };
  const handleRemoveMNT = () => {
    isShowCreateSubscribeRule.value = true;
  };

  const handleCopyClusterMasterDomainAndLink = () => {
    const { href } = router.resolve({
      name: 'tendbClusterDetail',
      params: {
        clusterId: props.clusterId,
      },
    });

    execCopy(`${data.value?.master_domain}\n${getSelfDomain()}${href}`);
  };

  const handleCopyLink = () => {
    const { href } = router.resolve({
      name: 'tendbClusterDetail',
      params: {
        clusterId: props.clusterId,
      },
    });
    execCopy(`${getSelfDomain()}${href}`);
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
