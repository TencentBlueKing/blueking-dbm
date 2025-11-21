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
  <TicketInfoTable
    :data="tableData"
    row-key="host">
    <TicketInfoTableColumn
      col-key="host"
      :get-copy-value="(row: RowData) => `${row.host}:${row.port}`"
      :title="t('源实例')">
      <template #default="{ row }:{ row: RowData }">
        <span>{{ row.host }}:{{ row.port }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_pos"
      :title="t('迁移目标位置')" />
    <TicketInfoTableColumn
      col-key="repl_binlog_file"
      title="binlog file" />
    <TicketInfoTableColumn
      col-key="repl_binlog_pos"
      title="binlog pos" />
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Dumper } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Dumper.SwitchNodes>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number]['switch_instances'][number];

  defineOptions({
    name: TicketTypes.TBINLOGDUMPER_SWITCH_NODES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  const tableData = infos[0].switch_instances;
</script>
