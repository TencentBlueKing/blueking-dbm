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

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Dumper.SwitchNodes>;
  }

  defineOptions({
    name: TicketTypes.TBINLOGDUMPER_SWITCH_NODES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  const tableData = infos[0].switch_instances;

  const columns = [
    {
      field: 'host',
      label: t('源实例'),
      render: ({ data }: { data: { host: string; port: number } }) => (
        <span>
          {data.host}:{data.port}
        </span>
      ),
    },
    {
      field: 'target_pos',
      label: t('迁移目标位置'),
    },
    {
      field: 'repl_binlog_file',
      label: 'binlog file',
    },
    {
      field: 'repl_binlog_pos',
      label: 'binlog pos',
    },
  ];
</script>
