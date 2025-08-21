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
    <InfoItem :label="t('所属业务')">
      {{ ticketDetails.bk_biz_name || '--' }}
    </InfoItem>
    <InfoItem :label="t('指定执行时间')">
      {{ utcDisplayTime(ticketDetails.details.timing) || '--' }}
    </InfoItem>
    <InfoItem :label="t('自动修复')">
      {{ ticketDetails.details.data_repair.is_repair ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('全局超时时间（h）')">
      {{ ticketDetails.details.runtime_hour }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="tableData"
    :show-overflow="false"
    :merge-cells="mergeCells">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验从库')"
      :min-width="150">
      <template #header>
        <span class="mysql-checksum-ip-header">
          <span>{{ t('校验从库') }}</span>
          <PopoverCopy class="copy-btn">
            <div @click="() => handleCopySlave('ip')">
              {{ t('复制IP') }}
            </div>
            <div @click="() => handleCopySlave('instance')">
              {{ t('复制实例') }}
            </div>
          </PopoverCopy>
        </span>
      </template>
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="(item, index) in data.slaves"
          :key="index">
          <p class="pt-2 pb-2">{{ item.ip }}:{{ item.port }}</p>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('校验主库')"
      :min-width="150">
      <template #header>
        <span class="mysql-checksum-ip-header">
          <span>{{ t('校验主库') }}</span>
          <PopoverCopy class="copy-btn">
            <div @click="() => handleCopyMaster('ip')">
              {{ t('复制IP') }}
            </div>
            <div @click="() => handleCopyMaster('instance')">
              {{ t('复制实例') }}
            </div>
          </PopoverCopy>
        </span>
      </template>
      <template #default="{ data }: { data: RowData }"> {{ data.master.ip }}:{{ data.master.port }} </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.db_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_dbs" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('校验表名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.table_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略表名')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.ignore_tables" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  import PopoverCopy from '@components/popover-copy/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.CheckSum>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_CHECKSUM,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = shallowRef<RowData[]>([]);

  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  watch(
    () => props.ticketDetails.details.infos,
    () => {
      const clusterMap: Record<string, RowData[]> = {};
      props.ticketDetails.details.infos.forEach((item) => {
        const clusterId = item.cluster_id;
        if (!clusterMap[clusterId]) {
          clusterMap[clusterId] = [item];
        } else {
          clusterMap[clusterId].push(item);
        }
      });

      Object.values(clusterMap).forEach((list) => {
        const preRow = mergeCells.value[mergeCells.value.length - 1] || {
          col: 0,
          colspan: 1,
          row: 0,
          rowspan: 1,
        };
        mergeCells.value.push({
          col: 0,
          colspan: 1,
          row: preRow.row + preRow.rowspan - 1,
          rowspan: list.length,
        });
        tableData.value.push(...list);
      });
    },
    {
      immediate: true,
    },
  );

  const handleCopySlave = (field: 'ip' | 'instance') => {
    const slaves = tableData.value.reduce<RowData['slaves']>((acc, item) => {
      if (item.slaves.length) {
        return [...acc, ...item.slaves];
      }
      return acc;
    }, []);
    const items = slaves.map((item) => (item && field === 'instance' ? `${item.ip}:${item.port}` : item.ip));
    if (items.length > 0) {
      execCopy(items.join('\n'), t('复制成功，共n条', { n: items.length }));
    }
  };

  const handleCopyMaster = (field: 'ip' | 'instance') => {
    const items = tableData.value.map((item) =>
      item.master && field === 'instance' ? `${item.master.ip}:${item.master.port}` : item.master.ip,
    );
    if (items.length > 0) {
      execCopy(items.join('\n'), t('复制成功，共n条', { n: items.length }));
    }
  };
</script>
<style lang="less">
  .mysql-checksum-ip-header {
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
