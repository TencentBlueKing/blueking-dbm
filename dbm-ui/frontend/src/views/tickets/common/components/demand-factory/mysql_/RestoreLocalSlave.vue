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
    <InfoItem :label="t('备份源:')">
      {{ ticketDetails.details.infos.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <!-- <BkTableColumn :label="t('集群ID')">
      <template #default="{ data }: { data: RowData }">
        {{ data.cluster_id }}
      </template>
    </BkTableColumn> -->
    <BkTableColumn :label="t('所属集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
        <div class="cluster-name__alias">{{ ticketDetails.details.clusters[data.cluster_id].name }}</div>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标从库实例')">
      <template #default="{ data }: { data: RowData }">
        {{ data.slave.ip }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.RestoreLocalSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
