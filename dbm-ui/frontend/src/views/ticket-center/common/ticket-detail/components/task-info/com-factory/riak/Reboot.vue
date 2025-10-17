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
  <PrimaryTable :data="dataList">
    <TableColumn
      col-key="cluster_id"
      :title="t('集群ID')">
      <template #default="{ row }">
        <span>{{ row.cluster_id || '--' }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="immute_domain"
      :ellipsis="false"
      :title="t('集群名称')">
      <template #default="{ row }">
        <div>
          <span>{{ row.immute_domain }}</span>
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_type_name"
      :title="t('集群类型')">
      <template #default="{ row }">
        <span>{{ row.cluster_type_name || '--' }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="node_ip"
      :title="t('节点IP')">
      <template #default="{ row }">
        <p class="pt-2 pb-2">
          {{ row.node_ip }}
          <DbIcon
            v-bk-tooltips="t('复制IP')"
            type="copy"
            @click="execCopy(row.node_ip, t('复制成功，共n条', { n: 1 }))" />
        </p>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Riak } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Riak.Reboot>;
  }

  defineOptions({
    name: TicketTypes.RIAK_CLUSTER_REBOOT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = computed(() => {
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};

    return [
      {
        cluster_id: clusterId,
        cluster_type_name: clusters.cluster_type_name,
        immute_domain: clusters.immute_domain,
        name: clusters.name,
        node_ip: props.ticketDetails?.details?.ip,
      },
    ];
  });
</script>
