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
  <PrimaryTable
    class="details-cluster__table"
    :data="dataList">
    <TableColumn
      col-key="cluster_id"
      :title="t('集群ID')">
      <template #default="{ row: data }: { row: ClusterItem }">
        <span>{{ data.id || '--' }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="immute_domain"
      :title="t('集群名称')">
      <template #default="{ row: data }: { row: ClusterItem }">
        <span>{{ data.immute_domain }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_type_name"
      :title="t('集群类型')">
      <template #default="{ row: data }: { row: ClusterItem }">
        <span>{{ data.cluster_type_name || '--' }}</span>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  type ClusterItem = {
    cluster_type_name: string;
    id: number;
    immute_domain: string;
    name: string;
  };

  interface Props {
    ticketDetails: TicketModel<Mongodb.Destroy>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters } = props.ticketDetails.details;
  const dataList = Object.keys(clusters).reduce((prevData, clusterId) => {
    const clusterItem = clusters[Number(clusterId)];
    return [
      ...prevData,
      {
        cluster_type_name: clusterItem.cluster_type_name,
        id: clusterItem.id,
        immute_domain: clusterItem.immute_domain,
        name: clusterItem.name,
      },
    ];
  }, [] as ClusterItem[]);
</script>
