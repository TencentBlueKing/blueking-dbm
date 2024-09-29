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
    <InfoItem :label="t('数据校验:')">
      {{ ticketDetails.details.need_checksum ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('校验时间:')">
      {{ isTimer ? t('定时执行') : t('立即执行') }}
    </InfoItem>
    <InfoItem
      v-if="isTimer"
      :label="t('定时执行时间:')">
      {{ utcDisplayTime(ticketDetails.details.trigger_checksum_time) }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      fixed="left"
      :label="t('目标集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('当前资源规格')">
      <template #default="{ data }: { data: RowData }">
        {{ data.prev_cluster_spec_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('集群分片数')">
      <template #default="{ data }: { data: RowData }">
        {{ data.cluster_shard_num }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('部署机器组数')">
      <template #default="{ data }: { data: RowData }">
        {{ data.prev_machine_pair }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('当前总容量')">
      <template #default="{ data }: { data: RowData }">
        {{ data.prev_cluster_spec_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标总容量')">
      <template #default="{ data }: { data: RowData }">
        {{ specInfoMap[data.resource_spec.backend_group.spec_id]?.spec_name }}
      </template>
    </BkTableColumn>
  </BkTable>
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

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const isTimer = props.ticketDetails.details.trigger_checksum_type === 'timer';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const specInfoMap = shallowRef<Record<number, ResourceSpecModel>>({});

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: DBTypes.TENDBCLUSTER,
        limit: -1,
        offset: 0,
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
