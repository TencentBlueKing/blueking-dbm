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
  <TicketInfoTable
    :data="props.ticketDetails.details.infos"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="280"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="slave"
      :min-width="150"
      :title="t('校验从库')">
      <template #title>
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
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="(item, index) in row.slaves"
          :key="index">
          <p class="pt-2 pb-2">{{ item.ip }}:{{ item.port }}</p>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="master"
      :min-width="150"
      :title="t('校验主库')">
      <template #title>
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
      <template #default="{ row }: { row: RowData }"> {{ row.master.ip }}:{{ row.master.port }} </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_patterns"
      :title="t('校验 DB 名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.db_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_dbs"
      :title="t('忽略 DB 名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_dbs" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="table_patterns"
      :title="t('校验表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.table_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_tables"
      :title="t('忽略表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_tables" />
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import { execCopy, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

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

  const handleCopySlave = (field: 'ip' | 'instance') => {
    const slaves = props.ticketDetails.details.infos.reduce<RowData['slaves']>((acc, item) => {
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
    const items = props.ticketDetails.details.infos.map((item) =>
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
