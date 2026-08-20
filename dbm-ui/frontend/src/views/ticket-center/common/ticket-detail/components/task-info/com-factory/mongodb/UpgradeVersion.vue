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
  <InfoList>
    <InfoItem :label="t('升级策略:')">
      {{ strategyTextMap[ticketDetails.details.infos?.[0]?.strategy] ?? '--' }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="tableData"
    row-key="cluster_id_list">
    <TicketInfoTableColumn
      col-key="cluster_id_list"
      :get-copy-value="
        (item: RowData) => item.cluster_id_list.map((clusterId) => ticketDetails.details.clusters[clusterId].immute_domain)
      "
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.cluster_id_list"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type"
      :title="t('集群类型')">
      <template #default="{ row }: { row: RowData }">
        <DbTag
          v-if="row.cluster_type === ClusterTypes.MONGO_REPLICA_SET"
          theme="info">
          {{ t('副本集') }}
        </DbTag>
        <DbTag
          v-else-if="row.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER"
          theme="success">
          {{ t('分片集群') }}
        </DbTag>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_version"
      :title="t('当前版本')" />
    <TicketInfoTableColumn
      col-key="dest_version"
      :title="t('目标版本')" />
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';
  import TicketModel from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.UpgradeVersion>;
  }

  interface RowData {
    cluster_id_list: number[];
    cluster_type: ClusterTypes;
    current_version: string;
    dest_version: string;
    strategy: string;
  }

  defineOptions({
    name: TicketTypes.MONGODB_UPGRADE_VERSION,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const strategyTextMap: Record<string, string> = {
    full_stop: t('停机升级'),
    rolling: t('滚动升级'),
  };

  // 单据详情数据回显
  const tableData = computed<RowData[]>(() => {
    const { clusters, infos } = props.ticketDetails.details;

    if (!infos?.length || !clusters) {
      return [];
    }

    return infos.map((item) => ({
      cluster_id_list: item.cluster_id_list,
      cluster_type: clusters[item.cluster_id_list[0]]?.cluster_type ?? '--',
      current_version: item.current_version,
      dest_version: item.dest_version,
      strategy: item.strategy,
    }));
  });
</script>
