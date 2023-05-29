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
  <BkLoading :loading="loading">
    <DbOriginalTable
      class="details-backup__table"
      :columns="columns"
      :data="tableData" />
  </BkLoading>
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('忽略业务连接') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMongoList } from '@services/source/mongodb';
  import type { TicketDetails } from '@services/types/ticket';

  interface ShardScaleDownDetails {
    clusters: Record<number, {
      alias: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      creator: string;
      db_module_id: number;
      disaster_tolerance_level: string;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      phase: string;
      region: string;
      status: string;
      tag: {
        bk_biz_id: number;
        name: string;
        type: string;
      }[];
      time_zone: string;
      updater: string;
    }>;
    infos: {
      cluster_id: number;
      reduce_shard_nodes: number;
    }[];
    is_safe: boolean;
    ip_source: string;
  }

  interface Props {
    ticketDetails: TicketDetails<ShardScaleDownDetails>
  }

  interface RowData {
    immute_domain: string,
    cluster_type: string,
    current_nodes: number,
    reduce_shard_nodes: number,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const {
    clusters,
    infos,
  } = props.ticketDetails.details;

  const columns = [
    {
      label: t('目标集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('集群类型'),
      field: 'cluster_type',
      showOverflowTooltip: true,
    },
    {
      label: t('当前Shard的节点数'),
      field: 'current_nodes',
      showOverflowTooltip: true,
    },
    {
      label: t('缩容至（节点数）'),
      field: 'reduce_shard_nodes',
      showOverflowTooltip: true,
    },
  ];

  const {
    loading,
    run: fetchMongoList,
  } = useRequest(getMongoList, {
    manual: true,
    onSuccess(result) {
      const shardNumMap = result.results.reduce((results, item) => {
        Object.assign(results, {
          [item.id]: item.shard_node_count,
        });
        return results;
      }, {} as Record<number, number>);
      tableData.value = infos.map(item => ({
        immute_domain: clusters[item.cluster_id].immute_domain,
        cluster_type: clusters[item.cluster_id].cluster_type_name,
        reduce_shard_nodes: shardNumMap[item.cluster_id] - item.reduce_shard_nodes,
        current_nodes: shardNumMap[item.cluster_id],
      }));
    },
  });

  fetchMongoList({
    domains: props.ticketDetails.details.infos.map(item => clusters[item.cluster_id].immute_domain).join(','),
  });


</script>
<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
@import "@views/tickets/common/styles/ticketDetails.less";

.ticket-details {
  &__info {
    padding-left: 80px;
  }

  &__item {
    &-label {
      min-width: 0;
      text-align: left;
    }
  }
}

.details-backup {
  &__table {
    padding-left: 80px;
  }
}
</style>
