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
          v-db-console="'sqlserver.singleClusterList.authorize'"
          class="ml-8"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <OperationBtnStatusTips
          v-db-console="'sqlserver.singleClusterList.enable'"
          :data="data">
          <BkButton
            class="ml-8"
            :disabled="data.isStarting"
            size="small"
            @click="handleEnableCluster([data])">
            {{ t('启用') }}
          </BkButton>
        </OperationBtnStatusTips>
        <OperationBtnStatusTips
          v-db-console="'sqlserver.singleClusterList.reset'"
          :data="data">
          <BkButton
            class="ml-8"
            :disabled="Boolean(data.operationTicketId)"
            size="small"
            @click="handleResetCluster">
            {{ t('重置') }}
          </BkButton>
        </OperationBtnStatusTips>
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
          <BkDropdownItem v-db-console="'sqlserver.singleClusterList.disable'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                :disabled="data.isOffline || Boolean(data.operationTicketId)"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </BkButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'sqlserver.singleClusterList.delete'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                text
                @click="handleDeleteCluster([data])">
                {{ t('删除') }}
              </BkButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
        </MoreActionExtend>
        <RouterLink
          v-if="!isDetailPage"
          style="margin-left: auto"
          target="_blank"
          :to="{
            name: 'SqlServerSingleClusterDetail',
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
        :cluster-type="ClusterTypes.SQLSERVER_SINGLE">
        <template #infoContent>
          <BaseInfo :data="data" />
        </template>
      </ActionPanel>
      <!-- 集群授权 -->
      <ClusterAuthorize
        v-model="isAuthorizeShow"
        :account-type="AccountTypes.SQLSERVER"
        :cluster-types="[ClusterTypes.SQLSERVER_SINGLE]"
        :selected="[data]" />
      <!-- excel 导入授权 -->
      <ExcelAuthorize
        v-model:is-show="isShowExcelAuthorize"
        :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
        :ticket-type="TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES" />
      <ClusterReset
        v-model:is-show="isShowClusterReset"
        :data="data" />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import SqlServerSingleDetailModel from '@services/model/sqlserver/sqlserver-single-detail';
  import { getSingleClusterDetail } from '@services/source/sqlserverSingleCluster';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ActionPanel from '@views/db-manage/common/cluster-details/ActionPanel.vue';
  import DisplayBox from '@views/db-manage/common/cluster-details/DisplayBox.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterReset from '@views/db-manage/sqlserver/components/cluster-reset/Index.vue';

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

  const isDetailPage = 'SqlServerSingleClusterDetail' === (route.name as string);

  const data = ref<SqlServerSingleDetailModel>();

  /** 集群授权 */
  const isAuthorizeShow = ref(false);
  const isShowClusterReset = ref(false);
  const isShowExcelAuthorize = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    return {
      [t('实例')]: data.value?.storages || [],
    };
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getSingleClusterDetail, {
    manual: true,
    onSuccess(result: SqlServerSingleDetailModel) {
      data.value = result;
    },
  });

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
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

  const handleResetCluster = () => {
    isShowClusterReset.value = true;
  };

  const handleCopyClusterMasterDomainAndLink = () => {
    const { href } = router.resolve({
      name: 'SqlServerSingleClusterDetail',
      params: {
        clusterId: props.clusterId,
      },
    });

    execCopy(`${data.value?.master_domain}\n${getSelfDomain()}${href}`);
  };

  const handleCopyLink = () => {
    const { href } = router.resolve({
      name: 'SqlServerSingleClusterDetail',
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
