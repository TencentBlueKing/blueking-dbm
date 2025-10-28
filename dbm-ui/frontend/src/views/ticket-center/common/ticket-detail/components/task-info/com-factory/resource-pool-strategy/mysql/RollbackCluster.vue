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
    <InfoItem :label="t('构造类型')">
      {{ rollbackTypetitle[ticketDetails.details.rollback_cluster_type] }}
    </InfoItem>
  </InfoList>
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(item: RowData) => ticketDetails.details.clusters[item.cluster_id].immute_domain"
      :min-width="180"
      :title="t('待回档集群')">
      <template #default="{ row:data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      v-if="['BUILD_INTO_EXIST_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      col-key="target_cluster_id"
      :min-width="180"
      :title="t('目标集群')">
      <template #default="{ row:data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.target_cluster_id]?.immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      v-if="['BUILD_INTO_NEW_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)"
      col-key="rollback_host"
      :min-width="180"
      :title="t('回档到新主机')">
      <template #default="{ row:data }: { row: RowData }">
        {{ data.resource_spec.rollback_host.hosts[0].ip }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="backup_source"
      :min-width="100"
      :title="t('备份源')">
      <template #default="{ row:data }: { row: RowData }">
        {{ backupSourcetitle[data.backup_source] }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="rollback_time"
      :min-width="300"
      :title="t('回档类型')">
      <template #default="{ row:data }: { row: RowData }">
        <div v-if="data.rollback_time">{{ t('回档到指定时间：') }}{{ data.rollback_time }}</div>
        <div v-else-if="data.backupinfo.backup_id">
          {{ t('备份记录：') }}
          {{ dayjs(data.backupinfo.backup_time).format('YYYY-MM-DD HH:mm:ss ZZ') }}
        </div>
      </template>
    </InfoTableColumn>
    <template
      v-if="
        ['BUILD_INTO_NEW_CLUSTER', 'BUILD_INTO_EXIST_CLUSTER'].includes(ticketDetails.details.rollback_cluster_type)
      ">
      <InfoTableColumn
        col-key="databases"
        :min-width="120"
        :title="t('回档DB')">
        <template #default="{ row:data }: { row: RowData }">
          <BkTag
            v-for="item in data.databases"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.databases.length < 1">--</span>
        </template>
      </InfoTableColumn>
      <InfoTableColumn
        col-key="databases_ignore"
        :min-width="120"
        :title="t('忽略 DB')">
        <template #default="{ row:data }: { row: RowData }">
          <BkTag
            v-for="item in data.databases_ignore"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.databases_ignore.length < 1">--</span>
        </template>
      </InfoTableColumn>
      <InfoTableColumn
        col-key="tables"
        :min-width="120"
        :title="t('回档表名')">
        <template #default="{ row:data }: { row: RowData }">
          <BkTag
            v-for="item in data.tables"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.tables.length < 1">--</span>
        </template>
      </InfoTableColumn>
      <InfoTableColumn
        col-key="tables_ignore"
        :min-width="120"
        :title="t('忽略表名')">
        <template #default="{ row:data }: { row: RowData }">
          <BkTag
            v-for="item in data.tables_ignore"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.tables_ignore.length < 1">--</span>
        </template>
      </InfoTableColumn>
    </template>
  </InfoTable>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.RollbackCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const rollbackTypetitle = {
    BUILD_INTO_EXIST_CLUSTER: t('构造到已有集群'),
    BUILD_INTO_METACLUSTER: t('构造到原集群'),
    BUILD_INTO_NEW_CLUSTER: t('构造到新集群'),
  } as Record<string, string>;

  const backupSourcetitle = {
    local: t('本地备份'),
    remote: t('远程备份'),
  } as Record<string, string>;
</script>
