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
  <BkTable :data="dataList">
    <BkTableColumn
      fixed="left"
      :label="t('源集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="node_type"
      :label="t('节点类型')"
      :width="150">
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前使用的版本')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="item in data.current_versions"
          :key="item">
          {{ item }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="target_version"
      :label="t('目标版本')"
      :min-width="250">
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = { cluster_id: number } & Omit<Props['ticketDetails']['details']['infos'][number], 'cluster_ids'>;

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  defineOptions({
    name: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList: RowData[] = props.ticketDetails.details.infos.flatMap((infoItem) =>
    infoItem.cluster_ids.map((clusterId) => ({
      ...infoItem,
      cluster_id: clusterId,
    })),
  );
</script>
