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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      field="display_info.instance"
      :label="t('目标 Master 实例')">
    </BkTableColumn>
    <BkTableColumn
      field="cluster_id"
      :label="t('所属集群')"
      :rowspan="getRowSpan">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec"
      :label="t('规格')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs[data.resource_spec.backend_group.spec_id].name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="display_info.db_version"
      :label="t('版本')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="version in data.display_info.db_version"
          :key="version"
          style="line-height: 20px">
          {{ version }}
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type RedisClusterMigrate } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<RedisClusterMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
  });

  const { t } = useI18n();

  const getRowSpan = ({ row }: { row: RowData }) => {
    const { clusters, infos } = props.ticketDetails.details;
    return infos.filter((item) => clusters[item.cluster_id].immute_domain === clusters[row.cluster_id].immute_domain)
      .length;
  };
</script>
