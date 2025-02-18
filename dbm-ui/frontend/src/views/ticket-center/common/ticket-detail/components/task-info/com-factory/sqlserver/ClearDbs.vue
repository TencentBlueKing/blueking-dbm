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
      :label="t('集群')"
      :width="240">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('清档类型')">
      <template #default="{ data }: { data: RowData }">
        {{ clearModeMap[data.clean_mode] }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('指定 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.clean_dbs_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.clean_ignore_dbs_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('指定表名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.clean_tables" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略表名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_clean_tables" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('最终 DB')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.clean_dbs" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.ClearDbs>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_CLEAR_DBS,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const clearModeMap = {
    clean_tables: t('清理表数据'),
    drop_tables: t('删除表'),
    drop_dbs: t('删除整库'),
  } as Record<string, string>;
</script>
