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
        cluster-detail-router-name="SqlServerSingleClusterDetail"
        :data="data">
        <BkButton
          v-db-console="'sqlserver.singleClusterList.authorize'"
          class="ml-4"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <OperationBtnStatusTips
          v-db-console="'sqlserver.singleClusterList.enable'"
          :data="data">
          <BkButton
            class="ml-4"
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
            class="ml-4"
            :disabled="!data.isOffline"
            size="small"
            @click="handleResetCluster">
            {{ t('重置') }}
          </BkButton>
        </OperationBtnStatusTips>
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
          <BkDropdownItem>
            <ClusterDomainDnsRelation :data="data" />
          </BkDropdownItem>
        </MoreActionExtend>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.SQLSERVER_SINGLE">
        <template #infoContent>
          <BaseInfo
            :data="data"
            @refresh="fetchDetailData" />
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

  import SqlServerSingleDetailModel from '@services/model/sqlserver/sqlserver-single-detail';
  import { getSingleClusterDetail } from '@services/source/sqlserverSingleCluster';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import { ActionPanel, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterReset from '@views/db-manage/sqlserver/components/cluster-reset/Index.vue';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

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
    onSuccess(result) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.SQLSERVER,
    {
      onSuccess: () => {
        fetchDetailData();
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
      fetchDetailData();
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
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
