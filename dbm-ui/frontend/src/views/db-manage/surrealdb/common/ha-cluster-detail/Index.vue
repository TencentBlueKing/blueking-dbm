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
        cluster-detail-router-name="SurrealdbHaDetail"
        :data="data">
        <div
          v-if="data.isOnline"
          v-db-console="'surrealdb.haClusterList.disable'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_surrealdb_start"
              :disabled="Boolean(data.operationTicketId)"
              :permission="data.permission.k8s_surrealdb_start"
              :resource="data.id"
              size="small"
              @click="handleDisableCluster([data])">
              {{ t('禁用') }}
            </AuthButton>
          </OperationBtnStatusTips>
        </div>
        <div
          v-if="data.isOnline"
          v-db-console="'surrealdb.haClusterList.enable'"
          class="ml-4">
          <OperationBtnStatusTips :data="data">
            <AuthButton
              action-id="k8s_surrealdb_restart"
              :disabled="data.isStarting"
              :permission="data.permission.k8s_surrealdb_restart"
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
        :cluster-type="ClusterTypes.K8S_SURREALDB_HA">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
            :data="data"
            @refresh="fetchDetailData">
            <!-- <template #clbMaster>
              <ClbInfo
                :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
                :data="data" />
            </template> -->
            <template #k8sClusterName>
              <K8SClusterName
                :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
                :data="data" />
            </template>
            <template #spec>
              <K8SSpec
                :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
                :data="data" />
            </template>
          </BaseInfo>
        </template>
        <template #instanceContent>
          <K8SInstanceList
            :cluster-data="data"
            :cluster-type="ClusterTypes.K8S_SURREALDB_HA"
            :role="role"
            @refresh="handleRefresh">
            <template #role>
              <BkRadioGroup
                v-model="role"
                type="capsule">
                <BkRadioButton
                  v-for="item in roleList"
                  :key="item.id"
                  :label="item.id">
                  {{ item.name }}
                </BkRadioButton>
              </BkRadioGroup>
            </template>
          </K8SInstanceList>
        </template>
      </ActionPanel>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SurrealdbHaDetailModel from '@services/model/surrealdb/surrealdb-ha-detail';
  import { getSurrealdbHaDetail } from '@services/source/surrealdbHa';

  // import { getTendbhaDetail as getSurrealdbHaDetail } from '@services/source/tendbha';
  import { ClusterTypes } from '@common/const';

  import {
    ActionPanel,
    BaseInfo,
    // BaseInfoField,
    DisplayBox,
    K8SClusterName,
    K8SInstanceList,
    K8SSpec,
  } from '@views/db-manage/common/cluster-details';
  import { useK8sClusterRestart, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  import useRoleList from './useRoleList';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  // const { ClbInfo } = BaseInfoField;

  const { t } = useI18n();

  const data = ref<SurrealdbHaDetailModel>();
  const isLoading = ref(false);

  const { defaultRole: role, list: roleList } = useRoleList();
  const { run: fetchClusterDetail } = useRequest(getSurrealdbHaDetail, {
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
