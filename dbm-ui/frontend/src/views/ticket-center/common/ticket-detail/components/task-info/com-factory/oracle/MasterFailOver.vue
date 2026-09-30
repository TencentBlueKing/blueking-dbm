<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="master.ip">
    <TicketInfoTableColumn
      col-key="master"
      :get-copy-value="(row: IRowData) => row.master.ip"
      :title="t('主库主机')">
      <template #default="{ row }: { row: IRowData }">
        {{ row.master?.ip || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="slave"
      :get-copy-value="(row: IRowData) => row.slave?.ip"
      :title="t('从库主机')">
      <template #default="{ row }: { row: IRowData }">
        {{ row.slave?.ip || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: IRowData) => ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || ''"
      :title="t('关联集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_check_process ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { Oracle } from '@services/model/ticket/ticket';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type IRowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Oracle.oracleMasterFailOver>;
  }

  defineOptions({
    name: TicketTypes.ORACLE_MASTER_FAIL_OVER,
    inheritAttrs: false,
  });

  defineProps<Props>();
  const { t } = useI18n();
</script>
