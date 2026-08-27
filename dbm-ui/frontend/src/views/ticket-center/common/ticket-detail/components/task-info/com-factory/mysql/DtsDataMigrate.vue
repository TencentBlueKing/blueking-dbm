<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
-->

<template>
  <InfoList>
    <InfoItem :label="t('数据冲突处理')">
      {{ conflictHandleText || '--' }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="tableData"
    row-key="source_cluster">
    <TicketInfoTableColumn
      col-key="source_cluster"
      ellipsis
      fixed="left"
      :get-copy-value="(row: RowData) => row.source_cluster_domain"
      :min-width="240"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ row.source_cluster_domain || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="source_db_list"
      :min-width="180"
      :title="t('源 DB')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.source_db_list.length">
          <template v-if="expandedKeys.has(String(row.source_cluster))">
            <DbTag
              v-for="item in row.source_db_list"
              :key="item">
              {{ item }}
            </DbTag>
            <DbTag
              v-if="row.source_db_list.length > 5"
              @click="handleToggleExpand(row)">
              {{ t('收起') }}
            </DbTag>
          </template>
          <template v-else>
            <DbTag
              v-for="item in row.source_db_list.slice(0, 5)"
              :key="item">
              {{ item }}
            </DbTag>
            <DbTag
              v-if="row.source_db_list.length > 5"
              @click="handleToggleExpand(row)">
              {{ t('共n个', [row.source_db_list.length]) }}
            </DbTag>
          </template>
        </template>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_db_list"
      :min-width="180"
      :title="t('忽略 DB')">
      <template #default="{ row }: { row: RowData }">
        <DbTag
          v-for="item in row.ignore_db_list"
          :key="item">
          {{ item }}
        </DbTag>
        <span v-if="row.ignore_db_list.length < 1">--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="source_table_list"
      :min-width="180"
      :title="t('源表')">
      <template #default="{ row }: { row: RowData }">
        <DbTag
          v-for="item in row.source_table_list"
          :key="item">
          {{ item }}
        </DbTag>
        <span v-if="row.source_table_list.length < 1">--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_table_list"
      :min-width="180"
      :title="t('忽略表')">
      <template #default="{ row }: { row: RowData }">
        <DbTag
          v-for="item in row.ignore_table_list"
          :key="item">
          {{ item }}
        </DbTag>
        <span v-if="row.ignore_table_list.length < 1">--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_cluster"
      ellipsis
      :get-copy-value="(row: RowData) => row.target_cluster_domain"
      :min-width="240"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ row.target_cluster_domain || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="resource_spec"
      :min-width="160"
      :title="t('DTS 规格')">
      <template #default="{ row }: { row: RowData }">
        {{ row.spec_name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="140"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.label_names.length">
          <DbTag
            v-for="item in row.label_names"
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
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface RowData {
    ignore_db_list: string[];
    ignore_table_list: string[];
    label_names: string[];
    source_cluster: number;
    source_cluster_domain: string;
    source_db_list: string[];
    source_table_list: string[];
    spec_name: string;
    target_cluster: number;
    target_cluster_domain: string;
  }

  interface Props {
    ticketDetails: TicketModel<Mysql.DtsDataMigrate>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_DTS_DATA_MIGRATE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 源 DB 折叠展开状态（key 为源集群 ID）
  const expandedKeys = ref(new Set<string>());

  const handleToggleExpand = (row: RowData) => {
    const key = String(row.source_cluster);
    const newSet = new Set(expandedKeys.value);
    if (newSet.has(key)) {
      newSet.delete(key);
    } else {
      newSet.add(key);
    }
    expandedKeys.value = newSet;
  };

  const conflictHandleTextMap = {
    error: t('报错并停止'),
    ignore: t('保留旧数据'),
    replace: t('覆盖旧数据'),
  } as const;

  const conflictHandleText = computed(() => {
    const { on_duplicate: onDuplicate } = props.ticketDetails.details.task || {};
    return (onDuplicate && conflictHandleTextMap[onDuplicate]) || t('报错并停止');
  });

  // 从 infos[].migrate.one_to_one 提取行数据
  const tableData = computed<RowData[]>(() => {
    const { details } = props.ticketDetails;
    return details.infos.map((item) => ({
      ignore_db_list: item.migrate.one_to_one.source.sync_scope.ignore_dbs || [],
      ignore_table_list: (item.migrate.one_to_one.source.sync_scope.ignore_tables || []).map(
        (tableItem) => tableItem.table,
      ),
      label_names: item.resource_spec?.master?.label_names || [],
      source_cluster: item.migrate.one_to_one.source.cluster_id,
      source_cluster_domain: details.clusters?.[item.migrate.one_to_one.source.cluster_id]?.immute_domain || '--',
      source_db_list: item.migrate.one_to_one.source.sync_scope.do_dbs || [],
      source_table_list: (item.migrate.one_to_one.source.sync_scope.do_tables || []).map(
        (tableItem) => tableItem.table,
      ),
      spec_name: details.specs?.[item.resource_spec?.master?.spec_id]?.name || '',
      target_cluster: item.migrate.one_to_one.target.cluster_id,
      target_cluster_domain: details.clusters?.[item.migrate.one_to_one.target.cluster_id]?.immute_domain || '--',
    }));
  });
</script>
