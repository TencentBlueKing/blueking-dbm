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
  <DbOriginalTable
    class="details-backup__table"
    :columns="columns"
    :data="tableData" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('忽略业务连接') }}：</span>
      <span class="ticket-details-item-value">
        {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.AddShardNodes>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_ADD_SHARD_NODES,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const { clusters, infos } = props.ticketDetails.details;
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
      label: t('扩容至（节点数）'),
      field: 'add_shard_nodes_num',
      showOverflowTooltip: true,
    },
  ];

  const tableData = infos.map((item) => ({
    immute_domain: clusters[item.cluster_ids[0]].immute_domain,
    cluster_type: clusters[item.cluster_ids[0]].cluster_type_name,
    add_shard_nodes_num: item.add_shard_nodes_num,
    current_nodes: item.add_shard_nodes_num - item.resource_spec.shard_nodes.count,
  }));
</script>
<style lang="less" scoped>
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
