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
  <div class="ticket-details__info">
    <div
      class="ticket-details__item"
      style="align-items: flex-start">
      <span class="ticket-details__item-label">{{ t('需求信息') }}：</span>
      <span class="ticket-details__item-value">
        <BkLoading :loading="loading">
          <DbOriginalTable
            :columns="columns"
            :data="tableData" />
        </BkLoading>
      </span>
    </div>
  </div>

  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('指定执行时间') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.details.timing }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('全局超时时间（h）') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.runtime_hour }}
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('修复数据') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.data_repair.is_repair ? t('是') : t('否') }}
        </span>
      </div>
      <div
        v-if="ticketDetails.details.data_repair.is_repair"
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('修复模式') }}：</span>
        <span class="ticket-details__item-value">
          {{ repairModesMap[ticketDetails.details.data_repair.mode] }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpiderListByBizId } from '@services/source/spider';
  import type { SpiderCheckSumDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderCheckSumDetails>;
  }

  interface RowData {
    clusterName: string;
    scope: string;
    slave: string;
    master: string;
    dbName: string;
    ignoreDbName: string;
    tableName: string;
    ignoreTableName: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const repairModesMap = {
    timer: t('定时执行'),
    manual: t('手动执行'),
  };

  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('校验范围'),
      field: 'scope',
      showOverflowTooltip: true,
    },
    {
      label: t('校验从库'),
      field: 'slave',
      showOverflowTooltip: true,
    },
    {
      label: t('校验主库'),
      field: 'master',
      showOverflowTooltip: true,
    },
    {
      label: t('校验DB名'),
      field: 'dbName',
      showOverflowTooltip: true,
    },
    {
      label: t('忽略DB名'),
      field: 'ignoreDbName',
      showOverflowTooltip: true,
    },
    {
      label: t('校验表名'),
      field: 'tableName',
      showOverflowTooltip: true,
    },
    {
      label: t('忽略表名'),
      field: 'ignoreTableName',
      showOverflowTooltip: true,
    },
  ];

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
            dbName: row.db_patterns.join(','),
            tableName: row.table_patterns.join(','),
            ignoreDbName: row.ignore_dbs.join(','),
            ignoreTableName: row.ignore_tables.join(','),
          };
          results.push(obj);
        });
        return results;
      }, [] as RowData[]);
    },
  });
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
