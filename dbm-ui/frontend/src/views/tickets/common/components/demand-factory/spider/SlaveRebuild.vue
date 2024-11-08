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
    v-if="ticketDetails.ticket_type === TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE"
    class="details-slave__table"
    :columns="localSlaveColumns"
    :data="ticketDetails.details.infos" />
  <DbOriginalTable
    v-else
    class="details-slave__table"
    :columns="addSlaveColumns"
    :data="ticketDetails.details.infos" />
  <InfoList>
    <InfoItem :label="t('备份源：')">
      {{ ticketDetails.details.backup_source === 'remote' ? t('远程备份') : t('本地备份') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderSlaveRebuid } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<SpiderSlaveRebuid>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  type dataItem = {
    cluster_id: number;
    slave: string;
    new_slave: string;
    immute_domain: string;
    name: string;
    backup_source: string;
  };

  // 原地重建
  const localSlaveColumns = [
    {
      label: t('目标从库实例'),
      field: 'slave',
      render: ({ data }: { data: dataItem }) => `${data.slave.ip}:${data.slave.port}`,
    },
    {
      label: t('所属集群'),
      field: 'backup_source',
      render: ({ data }: { data: RowData }) => props.ticketDetails.details.clusters[data.cluster_id].immute_domain,
    },
  ];

  const addSlaveColumns = [
    {
      label: t('目标从库主机'),
      field: 'cluster_id',
      render: ({ data }: { data: RowData }) => data.old_slave.ip,
    },
    {
      label: t('从库主机关联实例'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: () => '--',
    },
    {
      label: t('同机关联集群'),
      field: 'cluster_id',
      render: ({ data }: { data: RowData }) => props.ticketDetails.details.clusters[data.cluster_id].immute_domain,
    },
    {
      label: t('当前资源规格'),
      field: 'resource_spec',
      render: ({ data }: { data: RowData }) => data.resource_spec.new_slave.name,
    },
    {
      label: t('新从库主机'),
      field: 'backup_source',
      render: () => t('资源池自动匹配'),
    },
  ];
</script>
