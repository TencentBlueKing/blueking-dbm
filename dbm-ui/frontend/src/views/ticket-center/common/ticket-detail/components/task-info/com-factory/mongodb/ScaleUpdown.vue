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
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ScaleUpdown>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_SCALE_UPDOWN,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const columns = [
    {
      label: t('目标分片集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('目标资源规格'),
      field: 'target_spec',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('目标Shard节点数'),
      field: 'shard_node_count',
    },
    {
      label: t('目标机器组数'),
      field: 'shard_machine_group',
    },
    {
      label: t('分片数'),
      field: 'shards_num',
    }
  ];

  const dataList = computed(() => {
    const {
      clusters,
      infos,
      specs,
    } = props.ticketDetails.details;
    return infos.map(item => ({
      immute_domain: clusters[item.cluster_id].immute_domain,
      target_spec: specs[item.resource_spec.mongodb.spec_id].name,
      shard_node_count: item.shard_node_count,
      shard_machine_group: item.shard_machine_group,
      shards_num: item.shards_num,
    }));
  });
</script>
