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
    :data="tableData">
    <TableColumn
      fixed="left"
      min-width="150"
      :title="t('实例')"
      width="200">
      <template #default="{ row: data }: { row: RowData }"> {{ data.ip }}:{{ data.listen_port }} </template>
    </TableColumn>
    <TableColumn
      :title="t('实例 ID')"
      width="80">
      <template #default="{ row: data }: { row: RowData }"> {{ data.dumper_id }} </template>
    </TableColumn>
    <TableColumn
      min-width="200"
      :title="t('数据源集群')"
      width="250">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.source_cluster.immute_domain }}:{{ data.source_cluster.master_port }}
      </template>
    </TableColumn>
    <TableColumn :title="t('接收端类型')">
      <template #default="{ row: data }: { row: RowData }"> {{ data.protocol_type }} </template>
    </TableColumn>
    <TableColumn :title="t('接收端地址')">
      <template #default="{ row: data }: { row: RowData }"> {{ data.target_address }}:{{ data.target_port }} </template>
    </TableColumn>
    <TableColumn :title="t('同步方式')">
      <template #default="{ row: data }: { row: RowData }"> {{ syncTypeMap[data.add_type] }} </template>
    </TableColumn>
  </DbOriginalTable>
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

</script>
