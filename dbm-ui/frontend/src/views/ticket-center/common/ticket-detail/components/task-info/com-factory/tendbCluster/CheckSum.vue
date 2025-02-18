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
  <BkTable
    :data="tableData"
    :merge-cells="mergeCells">
    <BkTableColumn
      fixed="left"
      :label="t('目标集群')"
      :width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      fixed="left"
      :label="t('校验范围')"
      :width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.checksum_scope === 'all' ? t('整个集群') : t('部分实例') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验从库')"
      :width="220">
      <template #default="{ data }: { data: RowData }">
        {{ data.slave || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验主库')"
      :width="220">
      <template #default="{ data }: { data: RowData }">
        {{ data.master || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验DB名')"
      :width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.db_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略DB名')"
      :width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_dbs" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验表名')"
      :width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.table_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略表名')"
      :width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_tables" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { type UnwrapRef, watchEffect } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.CheckSum>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_CHECKSUM,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const repairModesMap = {
    auto: t('自动修复'),
    manual: t('手动执行'),
  } as Record<string, string>;

  const tableData = shallowRef<
    (Pick<Props['ticketDetails']['details']['infos'][number], 'cluster_id' | 'checksum_scope'> &
      Props['ticketDetails']['details']['infos'][number]['backup_infos'][number])[]
  >([]);
  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  type RowData = UnwrapRef<typeof tableData>[number];

  watchEffect(() => {
    let rowIndex = 0;
    props.ticketDetails.details.infos.forEach((infoItem) => {
      infoItem.backup_infos.forEach((backupInfoItem) => {
        tableData.value.push({
          ...infoItem,
          ...backupInfoItem,
        });
      });
      mergeCells.value.push({
        row: rowIndex,
        rowspan: infoItem.backup_infos.length,
        col: 0,
        colspan: 1,
      });
      mergeCells.value.push({
        row: rowIndex,
        rowspan: infoItem.backup_infos.length,
        col: 1,
        colspan: 1,
      });
      rowIndex += infoItem.backup_infos.length;
    });
  });
</script>
