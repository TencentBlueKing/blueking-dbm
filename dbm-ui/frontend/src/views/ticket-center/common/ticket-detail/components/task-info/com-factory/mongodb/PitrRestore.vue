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
    <InfoItem :label="t('集群类型:')">
      {{ clusterTypeInfos[ticketDetails.details.cluster_type].name }}
    </InfoItem>
    <InfoItem :label="t('目标集群与构造设置:')">
      <BkTable :data="ticketDetails.details.cluster_ids.map((item) => ({ clusterId: item }))">
        <BkTableColumn
          fixed="left"
          :label="t('集群')"
          :width="300">
          <template #default="{ row }">
            {{ ticketDetails.details.clusters[row.clusterId].immute_domain }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          :label="t('版本')"
          :width="150">
          <template #default="{ row }">
            {{ ticketDetails.details.clusters[row.clusterId].major_version }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          :label="t('指定时间')"
          :min-width="240">
          <template #default="{ row }">
            {{ utcDisplayTime(ticketDetails.details.rollback_time[row.clusterId]) }}
          </template>
        </BkTableColumn>
      </BkTable>
    </InfoItem>
    <InfoItem :label="t('构造新主机规格:')">
      {{ ticketDetails.details.specs[ticketDetails.details.resource_spec.mongodb.spec_id].name }}
    </InfoItem>
    <InfoItem :label="t('每台主机构造 Shard 数量:')">
      {{ ticketDetails.details.instance_per_host }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { clusterTypeInfos, TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.PitrRestore>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_PITR_RESTORE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
