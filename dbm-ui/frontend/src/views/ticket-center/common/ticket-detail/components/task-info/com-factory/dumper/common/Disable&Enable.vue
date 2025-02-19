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

  import TicketModel, { type Dumper } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Dumper.EnableNodes>;
  }

  type RowData = Props['ticketDetails']['details']['dumpers'][string];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = props.ticketDetails.details.dumper_instance_ids.map(
    (id) => props.ticketDetails.details.dumpers[id],
  );

  const syncTypeMap = {
    full_sync: t('全量同步'),
    incr_sync: t('增量同步'),
  } as Record<string, string>;

  const columns = [
    {
      field: 'ip',
      fixed: 'left',
      label: t('实例'),
      minWidth: 150,
      render: ({ data }: { data: RowData }) => (
        <span>
          {data.ip}:{data.listen_port}
        </span>
      ),
      width: 200,
    },
    {
      field: 'dumper_id',
      label: t('实例 ID'),
      width: 80,
    },
    {
      field: 'source_cluster',
      label: t('数据源集群'),
      minWidth: 200,
      render: ({ data }: { data: RowData }) => (
        <span>
          {data.source_cluster.immute_domain}:{data.source_cluster.master_port}
        </span>
      ),
      width: 250,
    },
    {
      field: 'protocol_type',
      label: t('接收端类型'),
    },
    {
      field: 'target_address',
      label: t('接收端地址'),
      render: ({ data }: { data: RowData }) => (
        <span>
          {data.target_address}:{data.target_port}
        </span>
      ),
    },
    {
      field: 'add_type',
      label: t('同步方式'),
      render: ({ data }: { data: RowData }) => <span>{syncTypeMap[data.add_type]}</span>,
    },
  ];
</script>
