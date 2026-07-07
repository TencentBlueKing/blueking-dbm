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
        cluster-detail-router-name="SurrealdbSingleDetail"
        :data="data">
        <div
          v-if="data.isOnline"
          v-db-console="'surrealdb.singleClusterList.disable'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_surrealdb_enable_disable"
              :disabled="Boolean(data.operationTicketId)"
              :permission="data.permission.k8s_surrealdb_enable_disable"
              :resource="data.id"
              size="small"
              @click="handleDisableCluster([data])">
              {{ t('禁用') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </div>
        <div
          v-if="data.isOnline"
          v-db-console="'surrealdb.singleClusterList.enable'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_surrealdb_manage"
              :disabled="data.isStarting"
              :permission="data.permission.k8s_surrealdb_manage"
              :resource="data.id"
              size="small"
              @click="handleClusterRestart(data)">
              {{ t('重启') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </div>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="{}"
        :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
            :data="data"
            @refresh="fetchDetailData">
            <template #k8sClusterName>
              <K8SClusterName
                :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
                :data="data" />
            </template>
            <template #spec>
              <K8SSpec
                :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
                :data="data" />
            </template>
          </BaseInfo>
        </template>
        <template #instanceContent>
          <K8SInstanceList
            :cluster-data="data"
            :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
            role="surreal"
            @refresh="handleRefresh">
          </K8SInstanceList>
        </template>
      </ActionPanel>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SurrealdbSingleDetailModel from '@services/model/surrealdb/surrealdb-single-detail';
  import { getSurrealdbSingleDetail } from '@services/source/surrealdbSingle';

  import { ClusterTypes } from '@common/const';

  import {
    ActionPanel,
    BaseInfo,
    DisplayBox,
    K8SClusterName,
    K8SInstanceList,
    K8SSpec,
  } from '@views/db-manage/common/cluster-details';
  import { useK8sClusterRestart, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const data = ref<SurrealdbSingleDetailModel>();
  const isLoading = ref(false);

  const { run: fetchClusterDetail } = useRequest(getSurrealdbSingleDetail, {
    manual: true,
    onAfter() {
      isLoading.value = false;
    },
    onSuccess(result) {
      data.value = result;
    },
    pollingInterval: 10 * 1000,
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDisableCluster } = useOperateClusterBasic(ClusterTypes.K8S_SURREALDB, {
    onSuccess: () => {
      fetchDetailData();
      emits('change');
    },
  });

  const { handleClusterRestart } = useK8sClusterRestart(ClusterTypes.K8S_SURREALDB, {
    onSuccess: () => {
      fetchDetailData();
      emits('change');
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

  const handleRefresh = () => {
    fetchDetailData();
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
