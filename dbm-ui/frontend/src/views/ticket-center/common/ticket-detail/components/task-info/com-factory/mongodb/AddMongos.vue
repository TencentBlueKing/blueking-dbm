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
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.AddMongos>;
  }

  interface RowData {
    add_shard_num: number;
    immute_domain: string;
    node_type: string;
    sepc_name: string;
  }

  defineOptions({
    name: TicketTypes.MONGODB_ADD_MONGOS,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;

  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      field: 'immute_domain',
      label: t('目标分片集群'),
      showOverflowTooltip: true,
    },
    {
      field: 'node_type',
      label: t('扩容节点类型'),
    },
    {
      field: 'sepc_name',
      label: t('扩容规格'),
      showOverflowTooltip: true,
    },
    {
      field: 'add_shard_num',
      label: t('扩容数量（台）'),
    },
  ];

  tableData.value = infos.map((item) => ({
    add_shard_num: item.resource_spec.mongos.count,
    immute_domain: clusters[item.cluster_id].immute_domain,
    node_type: 'mongos',
    sepc_name: specs[item.resource_spec.mongos.spec_id].name,
  }));
</script>
