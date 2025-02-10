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
    <InfoItem :label="t('检查业务来源的连接:')">
      {{ ticketDetails.details.is_check_process ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('检查主从同步延迟:')">
      {{ ticketDetails.details.is_check_delay ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('检查主从数据校验结果:')">
      {{ ticketDetails.details.is_verify_checksum ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn :label="t('主库主机')">
      <template #default="{ data }: { data: RowData }">
        {{ data.switch_tuples[0]?.master?.ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('从库主机')">
      <template #default="{ data }: { data: RowData }">
        {{ data.switch_tuples[0]?.slave?.ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('所属集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.MasterSlaveSwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
