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
    <InfoItem :label="t('数据校验')">
      {{ ticketDetails.details.need_checksum ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('校验时间')">
      {{ isTimer ? t('定时执行') : t('立即执行') }}
    </InfoItem>
    <InfoItem
      v-if="isTimer"
      :label="t('定时执行时间:')">
      {{ utcDisplayTime(ticketDetails.details.trigger_checksum_time) }}
    </InfoItem>
  </InfoList>
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TableColumn
      col-key="cluster_id"
      fixed="left"
      :min-width="220"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="prev_cluster_spec_name"
      :title="t('当前资源规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.prev_cluster_spec_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_shard_num"
      :title="t('集群分片数')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.cluster_shard_num }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="prev_machine_pair"
      :title="t('部署机器组数')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.prev_machine_pair }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="prev_cluster_spec_name"
      :title="t('当前总容量')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.prev_cluster_spec_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="spec_id"
      :title="t('目标总容量')">
      <template #default="{ row: data }: { row: RowData }">
        {{ specInfoMap[data.resource_spec.backend_group.spec_id]?.spec_name }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { DBTypes, TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.NodeRebalance>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isTimer = props.ticketDetails.details.trigger_checksum_type === 'timer';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const specInfoMap = shallowRef<Record<number, ResourceSpecModel>>({});

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
        spec_cluster_type: DBTypes.TENDBCLUSTER,
      },
    ],
    onSuccess(data) {
      specInfoMap.value = data.results.reduce(
        (result, item) =>
          Object.assign(result, {
            [item.spec_id]: item,
          }),
        {},
      );
    },
  });
</script>
