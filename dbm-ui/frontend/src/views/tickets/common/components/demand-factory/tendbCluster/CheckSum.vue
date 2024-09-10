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
    <InfoItem :label="t('指定执行时间:')">
      {{ utcDisplayTime(ticketDetails.details.timing) }}
    </InfoItem>
    <InfoItem :label="t('全局超时时间（h）:')">
      {{ ticketDetails.details.runtime_hour }}
    </InfoItem>
    <InfoItem :label="t('修复数据:')">
      {{ ticketDetails.details.data_repair.is_repair ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.data_repair.is_repair"
      :label="t('修复模式:')">
      {{ repairModesMap[ticketDetails.details.data_repair.mode] }}
    </InfoItem>
  </InfoList>
  <BkLoading :loading="loading">
    <BkTable :data="tableData">
      <BkTableColumn :label="t('目标集群')">
        <template #default="{ data }: { data: RowData }">
          {{ data.clusterName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('校验范围')">
        <template #default="{ data }: { data: RowData }">
          {{ data.scope }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('校验从库')">
        <template #default="{ data }: { data: RowData }">
          {{ data.slave }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('校验主库')">
        <template #default="{ data }: { data: RowData }">
          {{ data.master }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('校验DB名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.db_patterns"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.db_patterns.length < 1">--</span>
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
      <BkTableColumn :label="t('校验表名')">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.table_patterns"
            :key="item">
            {{ item }}
          </BkTag>
          <span v-if="data.table_patterns.length < 1">--</span>
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

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.CheckSum>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_CHECKSUM,
  });

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;

  const repairModesMap = {
    timer: t('定时执行'),
    manual: t('手动执行'),
  };

  interface RowData {
    clusterName: string;
    scope: string;
    slave: string;
    master: string;
    db_patterns: string;
    ignore_dbs: string;
    table_patterns: string;
    ignore_tables: string;
  }

  const tableData = ref<RowData[]>([]);

  const { loading } = useRequest(getSpiderListByBizId, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
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
        item.backup_infos.forEach((row) => {
          const obj = {
            clusterName: clusterMap[item.cluster_id],
            scope: item.checksum_scope === 'all' ? t('整个集群') : t('部分实例'),
            slave: row.slave,
            master: row.master,
            db_patterns: row.db_patterns,
            table_patterns: row.table_patterns,
            ignore_dbs: row.ignore_dbs,
            ignore_tables: row.ignore_tables,
          };
          results.push(obj);
        });
        return results;
      }, [] as RowData[]);
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
