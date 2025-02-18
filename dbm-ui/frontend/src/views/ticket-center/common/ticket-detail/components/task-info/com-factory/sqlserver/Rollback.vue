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
    <InfoItem :label="t('构造类型：')">
      {{ ticketDetails.details.is_local ? t('原地定点构造') : t('定点构造到其他集群') }}
    </InfoItem>
  </InfoList>
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      fixed="left"
      :label="t('待回档集群')"
      :width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="!ticketDetails.details.is_local"
      fixed="left"
      :label="t('目标集群')"
      :width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.dst_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('回档类型')"
      :width="300">
      <template #default="{ data }: { data: RowData }">
        <div v-if="data.restore_time">{{ t('回档到指定时间：') }}{{ data.restore_time }}</div>
        <div v-else-if="data.restore_backup_file">
          {{ t('备份记录：') }}{{ data.restore_backup_file.role }}
          {{ dayjs(data.restore_backup_file.start_time).format('YYYY-MM-DD HH:mm:ss ZZ') }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('构造 DB')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.db_list" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_db_list" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('构造后 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.rename_infos.map((item) => item.target_db_name)" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.Rollback>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_ROLLBACK,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
