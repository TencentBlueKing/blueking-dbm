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
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('备份 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="dbName in data.db_list"
          :key="dbName">
          {{ dbName }}
        </BkTag>
        <span v-if="data.db_list.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="dbName in data.ignore_db_list"
          :key="dbName">
          {{ dbName }}
        </BkTag>
        <span v-if="data.ignore_db_list.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('最终 DB')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.backup_dbs"
          :key="item">
          {{ item }}
        </BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份方式：')">
      {{ ticketDetails.details.backup_type === 'full_backup' ? t('全量备份') : t('增量备份') }}
    </InfoItem>
    <InfoItem :label="t('备份位置：')">
      {{ ticketDetails.details.backup_place === 'master' ? t('主库主机') : t('--') }}
    </InfoItem>
    <InfoItem :label="t('备份保存时间：')">
      {{ fileTagMap[ticketDetails.details.file_tag] }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.BackupDb>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();
  defineOptions({
    name: TicketTypes.SQLSERVER_BACKUP_DBS,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const fileTagMap = {
    DBFILE1M: t('1 个月'),
    DBFILE6M: t('6 个月'),
    DBFILE1Y: t('1 年'),
    DBFILE3Y: t('3 年'),
    INCREMENT_BACKUP: t('15天'),
  } as Record<string, string>;
</script>
