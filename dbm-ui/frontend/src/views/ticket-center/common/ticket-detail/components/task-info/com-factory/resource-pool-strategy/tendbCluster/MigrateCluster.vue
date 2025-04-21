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
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('目标主库主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.old_master?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('主库主机关联实例')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.old_master?.[0]?.ip]?.related_instances?.length">
          <p
            v-for="item in ticketDetails.details.machine_infos[data.old_nodes.old_master?.[0]?.ip].related_instances"
            :key="item.instance">
            {{ item.instance }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标从库主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.old_slave?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('从库主机关联实例')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.old_slave?.[0]?.ip]?.related_instances?.length">
          <p
            v-for="item in ticketDetails.details.machine_infos[data.old_nodes.old_slave?.[0]?.ip].related_instances"
            :key="item.instance">
            {{ item.instance }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('所属集群')"
      :min-width="260">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.MigrateCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
