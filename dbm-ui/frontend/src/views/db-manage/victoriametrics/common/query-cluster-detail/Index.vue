<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
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
        cluster-detail-router-name="VictoriametricsQueryDetail"
        :data="data">
        <div
          v-if="data.isOnline"
          v-db-console="'victoriametrics.queryClusterList.disable'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_vm_enable_disable"
              :disabled="Boolean(data.operationTicketId)"
              :permission="data.permission.k8s_vm_enable_disable"
              :resource="data.id"
              size="small"
              @click="handleDisableCluster([data])">
              {{ t('禁用') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </div>
        <div
          v-if="data.isOnline"
          v-db-console="'victoriametrics.queryClusterList.restart'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_victoriametrics_manage"
              :disabled="data.isStarting"
              :permission="data.permission.k8s_victoriametrics_manage"
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
        :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
            :data="data"
            @refresh="fetchDetailData">
            <template #queryEntry>
              <template v-if="data.queryEntryDisplay">
                {{ data.queryEntryDisplay }}
                <DbIcon
                  class="entry-copy-icon"
                  type="copy"
                  @click="handleCopy(data.queryEntryDisplay)" />
              </template>
              <template v-else>--</template>
            </template>
            <template #storageNode>
              {{ data.storage_nodes || '--' }}
            </template>
            <template #k8sClusterName>
              <K8SClusterName
                :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
                :data="data" />
            </template>
            <template #spec>
              <K8SSpec
                :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
                :data="data" />
            </template>
          </BaseInfo>
        </template>
        <template #instanceContent>
          <K8SInstanceList
            :cluster-data="data"
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
            role="vmselect"
            @refresh="handleRefresh" />
        </template>
      </ActionPanel>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import VictoriametricsQueryDetailModel from '@services/model/victoriametrics/victoriametrics-query-detail';
  import { getVictoriametricsQueryDetail } from '@services/source/victoriametricsQuery';

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

  import { execCopy } from '@utils';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const data = ref<VictoriametricsQueryDetailModel>();
  const isLoading = ref(false);

  const { run: fetchClusterDetail } = useRequest(getVictoriametricsQueryDetail, {
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

  const { handleDisableCluster } = useOperateClusterBasic(ClusterTypes.K8S_VICTORIAMETRICS, {
    onSuccess: () => {
      fetchDetailData();
      emits('change');
    },
  });

  const { handleClusterRestart } = useK8sClusterRestart(ClusterTypes.K8S_VICTORIAMETRICS, {
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

  const handleCopy = (value: string) => {
    if (value) {
      execCopy(value);
    }
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;

    .entry-copy-icon {
      margin-left: 6px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
