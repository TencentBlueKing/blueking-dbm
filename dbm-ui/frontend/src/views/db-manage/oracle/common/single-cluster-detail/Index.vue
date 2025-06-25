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
        cluster-detail-router-name="OracleSingleDetail"
        :data="data">
        <BkDropdownItem v-db-console="'oracle.toolbox.sqlExecute'">
          <OperationBtnStatusTips :data="data">
            <RouterLink
              target="_blank"
              :to="{
                name: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
                query: {
                  masterDomain: data.master_domain,
                },
              }">
              <BkButton
                class="ml-4"
                size="small">
                {{ t('变更 SQL 执行') }}
              </BkButton>
            </RouterLink>
          </OperationBtnStatusTips>
        </BkDropdownItem>
        <!-- <ClusterDomainDnsRelation :data="data" /> -->
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE">
        <template #infoContent>
          <BaseInfo
            :data="data"
            @refresh="fetchDetailData" />
        </template>
      </ActionPanel>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import OracleSingleModel from '@services/model/oracle/oracle-single';
  import { getOracleSingleClusterDetail } from '@services/source/oracleSingleCluster';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { ActionPanel, DisplayBox } from '@views/db-manage/common/cluster-details';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';

  // import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const data = ref<OracleSingleModel>();

  const clusterRoleNodeGroup = computed(() => {
    return {
      Primary: data.value?.primaries || [],
    };
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getOracleSingleClusterDetail, {
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
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
