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
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="cluster_ids"
      fixed="left"
      :get-copy-value="(row: RowData) => row.cluster_ids.map(clusterId => ticketDetails.details.clusters[clusterId].immute_domain)"
      :min-width="340"
      :title="t('目标集群')">
      <template #default="{row}: {row: RowData}">
        <div
          v-for="item in row.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="related_instances"
      min-width="400"
      :title="t('关联实例')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="(item, index) in row.related_instances"
          :key="index">
          <div class="domain-item">{{ item.domain }}</div>
          <div
            v-for="(instance, instaneIndex) in item.instances"
            :key="instaneIndex"
            class="instance-item">
            --{{ instance }}
          </div>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="120"
      :title="t('目标规格')">
      <template #default="{row}: {row: RowData}">
        {{ ticketDetails.details.specs[row.resource_spec.mongodb.spec_id].name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.mongodb?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.mongodb.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.ResourcePool.ReplicasetMigrate>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REPLICASET_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
