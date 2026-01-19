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
    :data="ticketDetails.details.infos"
    row-key="ip">
    <TicketInfoTableColumn
      col-key="ip"
      :get-copy-value="(row: RowData) => row.ip"
      :title="t('目标主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.ip }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="related_instances"
      :title="t('关联实例')">
      <template #default="{ row }: { row: RowData }">
        <p>
          {{ row.master_domain }}
        </p>
        <p style="color: #979ba5">--{{ row.instance_address }}</p>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Mongodb.InstanceFixStatus['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.InstanceFixStatus>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_INSTANCE_FIX_STATUS,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
