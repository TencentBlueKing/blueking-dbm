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
    <InfoItem :label="t('集群')">
      {{ ticketDetails.details.clusters[ticketDetails.details.cluster_id].immute_domain }}
    </InfoItem>
  </InfoList>
  <InfoList>
    <InfoItem label="Topic">
      <BkTag
        v-for="topic in ticketDetails.details.topics"
        :key="topic">
        {{ topic }}
      </BkTag>
    </InfoItem>
    <InfoItem :label="t('速率')">
      {{ ticketDetails.details.throttle_rate ? ticketDetails.details.throttle_rate + ' byte/s' : '--' }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.instance_list">
    <BkTableColumn
      label="Broker"
      :min-width="200">
      <template #default="{ row }">
        <span>{{ row.ip }}:{{ row.port }}</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('主机 Agent 状态')"
      :min-width="200">
      <template #default="{ row }">
        <DbStatus
          v-if="instanceInfo?.[`${row.ip}:${row.port}`]?.agent_status === 1"
          theme="success">
          {{ t('正常') }}
        </DbStatus>
        <DbStatus
          v-else-if="instanceInfo?.[`${row.ip}:${row.port}`]?.agent_status === 0"
          theme="danger">
          {{ t('异常') }}
        </DbStatus>
        <span v-else>--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('部署时间')"
      :min-width="200">
      <template #default="{ row }">
        <span>{{ instanceInfo?.[`${row.ip}:${row.port}`]?.create_at || '--' }}</span>
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Kafka } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Kafka.Rebalance>;
  }

  defineOptions({
    name: TicketTypes.KAFKA_REBALANCE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const instanceInfo = computed(() =>
    Object.fromEntries((props.ticketDetails.details.instance_info || []).map((item) => [item.intance_address, item])),
  );
</script>
