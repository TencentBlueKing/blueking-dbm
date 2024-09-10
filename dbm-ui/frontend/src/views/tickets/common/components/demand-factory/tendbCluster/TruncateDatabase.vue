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
  <BkLoading :loading="loading">
    <BkTable :data="tableData">
      <BkTableColumn :label="t('目标集群')">
        <template #default="{ data }: { data: RowData }">
          {{ data.clusterName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('清档类型')">
        <template #default="{ data }: { data: RowData }">
          {{ data.type }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('目的DB名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.db_patterns"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.db_patterns.length < 1">--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('目的表名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.table_patterns"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.table_patterns.length < 1">--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('忽略DB名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.ignore_dbs"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.ignore_dbs.length < 1">--</span>
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('忽略表名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.ignore_tables"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.ignore_tables.length < 1">--</span>
        </template>
      </BkTableColumn>
    </BkTable>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getSpiderListByBizId } from '@services/source/spider';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.TruncateDataBase>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE,
  });

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  interface RowData {
    clusterName: string;
    type: string;
    dbName: string;
    ignoreDbName: string;
    tableName: string;
    ignoreTableName: string;
  }

  const tableData = ref<RowData[]>([]);

  const typesMap = {
    truncate_table: t('清除表数据_truncatetable'),
    drop_table: t('清除表数据和结构_droptable'),
    drop_database: t('删除整库_dropdatabase'),
  };

  const { loading } = useRequest(getSpiderListByBizId, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        offset: 0,
        limit: -1,
      },
    ],
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce(
        (obj, item) => {
          Object.assign(obj, { [item.id]: item.master_domain });
          return obj;
        },
        {} as Record<number, string>,
      );

      tableData.value = infos.reduce((results, item) => {
        const obj = {
          clusterName: clusterMap[item.cluster_id],
          type: typesMap[item.truncate_data_type],
          db_patterns: item.db_patterns,
          table_patterns: item.table_patterns,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
        };
        results.push(obj);
        return results;
      }, [] as RowData[]);
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
