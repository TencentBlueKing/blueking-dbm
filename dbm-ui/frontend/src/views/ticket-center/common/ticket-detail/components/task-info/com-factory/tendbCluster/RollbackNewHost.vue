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
    <InfoItem :label="t('回档类型')">
      {{ t('新机构造回档') }}
    </InfoItem>
    <InfoItem :label="t('回档方式')">
      {{ info.rollback_type.endsWith('_AND_TIME') ? t('指定时间回档') : t('指定备份记录回档') }}
    </InfoItem>
    <InfoItem :label="t('备份源')">
      {{ info.rollback_type.startsWith('LOCAL_') ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--'"
      :min-width="320"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        <span class="source-cluster">
          {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
        </span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      v-if="info.rollback_type.endsWith('_AND_TIME')"
      col-key="rollback_time"
      :min-width="180"
      :title="t('指定时间')">
      <template #default="{ row }: { row: RowData }">
        {{ row.rollback_time ? utcDisplayTime(row.rollback_time) : '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="backupinfo"
      :get-copy-value="(row: RowData) => row.backupinfo.backup_id || '--'"
      :min-width="400"
      :title="t('备份记录')">
      <template #default="{ row }: { row: RowData }">
        <div class="content-block">
          <div class="content-label">{{ t('备份记录 ：') }}</div>
          <div class="content-value">
            {{
              row.backupinfo.backup_consistent_time
                ? utcDisplayTime(row.backupinfo.backup_consistent_time)
                : '--'
            }}
          </div>
          <div class="content-label">{{ t('备份 ID ：') }}</div>
          <div class="content-value">
            {{ row.backupinfo.backup_id || '--' }}
          </div>
          <div class="content-label">{{ t('备份类型 ：') }}</div>
          <div class="content-value">
            <template v-if="row.backupinfo.backup_type_list?.length">
              <template
                v-for="item in row.backupinfo.backup_type_list"
                :key="item">
                <DbTag
                  v-if="backupTypeMap[item]"
                  :theme="backupTypeMap[item].theme">
                  {{ backupTypeMap[item].label }}
                </DbTag>
                <span v-else>--</span>
              </template>
            </template>
            <span v-else>--</span>
          </div>
          <div class="content-label">{{ t('备份范围 ：') }}</div>
          <div class="content-value">
            <span
              :class="{
                [`backup-method-sign-${row.backupinfo.backup_method}`]: backupMethodMap[row.backupinfo.backup_method || ''],
              }">
              {{ backupMethodMap[row.backupinfo.backup_method || ''] || '--' }}
            </span>
          </div>
          <div class="content-label">{{ t('文件大小 ：') }}</div>
          <div class="content-value">
            {{ row.backupinfo.total_filesize !== undefined ? bytePretty(row.backupinfo.total_filesize) : '--' }}
          </div>
          <div
            v-if="row.backupinfo.bill_id"
            class="content-label">
            {{ t('关联单据 ：') }}
          </div>
          <div
            v-if="row.backupinfo.bill_id"
            class="content-value">
            <RouterLink
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: row.backupinfo.bill_id,
                },
              }">
              {{ row.backupinfo.bill_id }}
            </RouterLink>
          </div>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="databases"
      :get-copy-value="(row: RowData) => row.databases"
      :min-width="200"
      :title="t('源 DB')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.databases" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="tables"
      :get-copy-value="(row: RowData) => row.tables"
      :min-width="200"
      :title="t('源表')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.tables" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="affect_database_list"
      :get-copy-value="(row: RowData) => row.affect_database_list || []"
      :min-width="200"
      :title="t('受影响的 DB')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.affect_database_list || []" />
      </template>
    </TicketInfoTableColumn>
    <!-- 待 PEER 确认详情接口的目标规格快照字段，不通过实时源集群反查历史规格。 -->
    <TicketInfoTableColumn
      col-key="targetSpec"
      :min-width="220"
      :title="t('目标规格')">
      <template #default>--</template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label"
      :get-copy-value="(row: RowData) => row.label?.label_names || []"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock
          v-if="row.label?.label_names?.length"
          :data="row.label.label_names" />
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

  import type TicketModel from '@services/model/ticket/ticket';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.RollbackNewHost>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_ROLLBACK_NEW_HOST,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();
  const { t } = useI18n();
  const info = computed(() => props.ticketDetails.details.infos[0]);

  const backupMethodMap = {
    full_by_regular: t('全库备份（例行）'),
    full_by_ticket: t('全库备份（单据）'),
    non_full_by_regular: t('非全库备份（例行）'), // 过滤掉，不展示
    partial_by_ticket: t('库表备份（单据）'),
  } as Record<string, string>;

  const backupTypeMap = {
    logical: {
      label: t('逻辑备份'),
      theme: 'info',
    },
    physical: {
      label: t('物理备份'),
      theme: 'warning',
    },
  } as Record<
    string,
    {
      label: string;
      theme: 'info' | 'warning';
    }
  >;
</script>
<style lang="less" scoped>
  .source-cluster {
    white-space: nowrap;
  }

  .content-block {
    display: grid;
    grid-template-columns: 80px minmax(0, 1fr);
    line-height: 24px;

    .content-label {
      text-align: right;
    }

    .content-value {
      white-space: nowrap;
    }

    // 全库备份（例行）
    .backup-method-sign-full_by_regular::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #3a84ff;
      content: '';
    }
    // 全库备份（单据）
    .backup-method-sign-full_by_ticket::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #2caf5e;
      content: '';
    }
    //库表备份（单据）
    .backup-method-sign-partial_by_ticket::before {
      display: inline-block;
      width: 8px;
      height: 8px;
      margin-right: 6px;
      background-color: #f59500;
      content: '';
    }
  }
</style>
