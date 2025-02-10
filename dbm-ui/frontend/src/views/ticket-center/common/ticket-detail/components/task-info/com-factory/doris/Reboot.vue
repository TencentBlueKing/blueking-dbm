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
  <BkTable :data="tableData">
    <BkTableColumn :label="t('集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('集群类型')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('节点IP')">
      <template #default="{ data }: { data: RowData }">
        {{ data.node_ip.join(',') }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Doris } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Doris.Reboot>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.DORIS_REBOOT,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const tableData = computed(() => {
    const {
      cluster_id: clusterId,
      clusters = {},
      instance_list: instanceList = [],
    } = props.ticketDetails?.details || {};
    const nodeIp = instanceList.map((k) => k.ip);
    return [
      {
        cluster_id: clusterId,
        node_ip: nodeIp,
        ...clusters[clusterId],
      },
    ];
  });

  type RowData = UnwrapRef<typeof tableData>[number];
</script>
