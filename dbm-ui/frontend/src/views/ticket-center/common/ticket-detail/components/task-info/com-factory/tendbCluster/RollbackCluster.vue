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
    <InfoItem :label="t('构造类型:')">
      {{ rollbackTypeLabel[ticketDetails.details.rollback_cluster_type] }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      fixed="left"
      :label="t('待回档集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="['BUILD_INTO_EXIST_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.target_cluster_id]?.immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="['BUILD_INTO_NEW_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      :label="t('存储层主机')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ data.rollback_host.remote_hosts[0].ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="['BUILD_INTO_NEW_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      :label="t('接入层主机')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ data.rollback_host.spider_host.ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('回档类型')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <div v-if="data.rollback_time">{{ t('回档到指定时间：') }}{{ data.rollback_time }}</div>
        <div v-else-if="data.backupinfo.backup_id">
          {{ t('备份记录：') }}
          {{ dayjs(data.backupinfo.backup_time).format('YYYY-MM-DD HH:mm:ss ZZ') }}
        </div>
      </template>
    </BkTableColumn>
    <template
      v-if="
        ['BUILD_INTO_NEW_CLUSTER', 'BUILD_INTO_EXIST_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)
      ">
      <BkTableColumn
        :label="t('回档DB')"
        :min-width="200">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.databases" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('忽略 DB')"
        :min-width="200">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.databases_ignore" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('回档表名')"
        :min-width="200">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.tables" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('忽略表名')"
        :min-width="200">
        <template #default="{ data }: { data: RowData }">
          <TagBlock :data="data.tables_ignore" />
        </template>
      </BkTableColumn>
    </template>
  </BkTable>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.RollbackCluster>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const rollbackTypeLabel = {
    BUILD_INTO_NEW_CLUSTER: t('构造到新集群'),
    BUILD_INTO_EXIST_CLUSTER: t('构造到已有集群'),
    BUILD_INTO_METACLUSTER: t('构造到原集群'),
  } as Record<string, string>;

  type RowData = Props['ticketDetails']['details']['infos'][number];
</script>
