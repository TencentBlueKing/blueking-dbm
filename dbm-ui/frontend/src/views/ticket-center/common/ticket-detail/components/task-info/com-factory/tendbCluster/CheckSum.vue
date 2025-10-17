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
    <InfoItem :label="t('指定执行时间')">
      {{ utcDisplayTime(ticketDetails.details.timing) }}
    </InfoItem>
    <InfoItem :label="t('全局超时时间（h）')">
      {{ ticketDetails.details.runtime_hour }}
    </InfoItem>
    <InfoItem :label="t('修复数据')">
      {{ ticketDetails.details.data_repair.is_repair ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.data_repair.is_repair"
      :label="t('修复模式')">
      {{ repairModesMap[ticketDetails.details.data_repair.mode] }}
    </InfoItem>
  </InfoList>
  <PrimaryTable
    :data="tableData"
    row-key="master"
    :rowspan-and-colspan="rowspanAndColspan">
    <TableColumn
      fixed="left"
      :title="t('目标集群')"
      :width="200">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      fixed="left"
      :title="t('校验范围')"
      :width="100">
      <template #default="{ row }: { row: RowData }">
        {{ row.checksum_scope === 'all' ? t('整个集群') : t('部分实例') }}
      </template>
    </TableColumn>
    <TableColumn
      :title="t('校验从库')"
      :width="220">
      <template #header>
        <span class="tendbcluster-checksum-ip-header">
          <span>{{ t('校验从库') }}</span>
          <PopoverCopy class="copy-btn">
            <div @click="() => handleCopy('slave', 'ip')">
              {{ t('复制IP') }}
            </div>
            <div @click="() => handleCopy('slave', 'instance')">
              {{ t('复制实例') }}
            </div>
          </PopoverCopy>
        </span>
      </template>
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.checksum_scope === 'all'">{{ t('全部') }}</span>
        <div v-else-if="row.slave">
          <p
            v-for="item in row.slave.split(',')"
            :key="item">
            {{ item }}
          </p>
        </div>
        <span v-else>--</span>
      </template>
    </TableColumn>
    <TableColumn
      :title="t('校验主库')"
      :width="220">
      <template #header>
        <span class="tendbcluster-checksum-ip-header">
          <span>{{ t('校验主库') }}</span>
          <PopoverCopy class="copy-btn">
            <div @click="() => handleCopy('slave', 'ip')">
              {{ t('复制IP') }}
            </div>
            <div @click="() => handleCopy('slave', 'instance')">
              {{ t('复制实例') }}
            </div>
          </PopoverCopy>
        </span>
      </template>
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.checksum_scope === 'all'">{{ t('全部') }}</span>
        <span v-else>
          {{ row.master || '--' }}
        </span>
      </template>
    </TableColumn>
    <TableColumn
      :title="t('校验DB名')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.db_patterns" />
      </template>
    </TableColumn>
    <TableColumn
      :title="t('忽略DB名')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_dbs" />
      </template>
    </TableColumn>
    <TableColumn
      :title="t('校验表名')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.table_patterns" />
      </template>
    </TableColumn>
    <TableColumn
      :title="t('忽略表名')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_tables" />
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import { execCopy, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.CheckSum>;
  }

  interface RowData {
    checksum_scope: string;
    cluster_id: number;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: string;
    slave: string;
    table_patterns: string[];
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_CHECKSUM,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const repairModesMap = {
    auto: t('自动修复'),
    manual: t('手动执行'),
  } as Record<string, string>;

  const tableData = shallowRef<RowData[]>([]);

  // 先构造表格数据
  const clusterMap = _.groupBy(props.ticketDetails.details.infos, 'cluster_id');
  tableData.value = Object.values(clusterMap).flatMap((list) =>
    list.flatMap((item) =>
      item.backup_infos.map((row) => ({
        ...row,
        checksum_scope: item.checksum_scope,
        cluster_id: item.cluster_id,
      })),
    ),
  );

  // 再行合并
  const groupedData = _.groupBy(tableData.value, 'cluster_id');
  const spanInfo = Object.values(groupedData).flatMap((list, index) => [{ rowIndex: index, rowspan: list.length }]);

  const rowspanAndColspan = ({ colIndex, rowIndex }: { colIndex: number; rowIndex: number }) => {
    const spanItem = spanInfo.find((item) => (colIndex === 0 || colIndex === 1) && item.rowIndex === rowIndex);
    if (spanItem) {
      return {
        rowspan: spanItem.rowspan,
      };
    }
    return {};
  };

  const handleCopy = (role: 'master' | 'slave', field: 'ip' | 'instance') => {
    const items = tableData.value.map((item) => (item[role] && field === 'ip' ? item[role].split(':')[0] : item[role]));
    if (items.length > 0) {
      execCopy(items.join('\n'), t('复制成功，共n条', { n: items.length }));
    }
  };
</script>
<style lang="less">
  .tendbcluster-checksum-ip-header {
    display: flex;

    &:hover {
      .copy-btn {
        display: block;
      }
    }

    .copy-btn {
      display: none;
      margin-left: 4px;
      cursor: pointer;
    }
  }
</style>
