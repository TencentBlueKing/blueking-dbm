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
    :data="props.ticketDetails.details.configs"
    row-key="config_id">
    <TicketInfoTableColumn
      col-key="config_id"
      :title="t('策略 ID')" />
    <TicketInfoTableColumn
      col-key="config_id"
      :get-copy-value="() => props.ticketDetails.details.clusters[props.ticketDetails.details.cluster_id].immute_domain"
      :title="t('集群')"
      width="240">
      <template #default>
        <span>{{ props.ticketDetails.details.clusters[props.ticketDetails.details.cluster_id].immute_domain }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="dblike"
      :title="t('DB 名')">
      <template #default="{ row }: { row: RowData }">
        <DbTag>
          {{ row.dblike }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="tblike"
      :title="t('表名')">
      <template #default="{ row }: { row: RowData }">
        <DbTag>
          {{ row.tblike }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="partition_column"
      :title="t('分区字段')" />
    <TicketInfoTableColumn
      col-key="partition_column_type"
      :title="t('字段类型')" />
    <TicketInfoTableColumn
      col-key="partition_time_interval"
      :title="t('分区间隔（天）')"
      width="160" />
    <TicketInfoTableColumn
      col-key="expire_time"
      :title="t('数据过期时间（天）')"
      width="160" />
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.PartitionV2>;
  }

  type RowData = Props['ticketDetails']['details']['configs'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PARTITION_V2,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
</script>
