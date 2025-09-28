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
      field="shard_name"
      fixed="left"
      :label="t('目标分片')"
      :min-width="250">
      <template #default="{data}: {data: RowData}">
        <div
          v-for="item in data.shard_name"
          :key="item">
          {{ item }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_id"
      :label="t('关联集群')"
      :width="340">
      <template #default="{data}: {data: RowData}">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="related_instances"
      :label="t('关联集群实例')"
      min-width="400">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in data.related_instances"
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
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec.mongodb.spec_id"
      :label="t('目标规格')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        {{ ticketDetails.details.specs[data.resource_spec.mongodb.spec_id].name }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.ShardMigrate>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_SHARD_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
