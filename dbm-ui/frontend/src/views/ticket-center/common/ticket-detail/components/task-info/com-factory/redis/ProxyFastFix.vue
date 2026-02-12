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
  <InfoList>
    <InfoItem :label="t('操作类型')">
      {{ infos[0].operate_type === 'PROXY_ENTRY_KICKOFF' ? t('Proxy 剔除') : t('Proxy 修复') }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="tableData"
    row-key="ip">
    <TicketInfoTableColumn
      col-key="ip"
      :get-copy-value="(row: RowData) => row.ip"
      :min-width="250"
      :title="t('Proxy 主机')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="city"
      :min-width="150"
      :title="t('地域')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="bk_sub_zone"
      :title="t('园区')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="domain"
      :min-width="200"
      :title="t('关联集群')">
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ProxyFastFix>;
  }

  defineOptions({
    name: TicketTypes.REDIS_PROXY_FAST_FIX,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  type RowData = (typeof tableData)[number];

  const { clusters, infos } = props.ticketDetails.details;
  const tableData = infos.flatMap((infoItem) =>
    infoItem.proxy.map((item) => ({
      bk_sub_zone: item.bk_sub_zone || '--',
      city: item.city || '--',
      domain: clusters[infoItem.cluster_id].immute_domain,
      ip: item.ip,
    })),
  );
</script>
