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
      <span class="ticket-details__item-label">{{ t('订阅的库表') }}：</span>
      <span class="ticket-details__item-value">
        <BkTable
          class="subscribe-table"
          :columns="subscribeColumns"
          :data="subscribeTableData" />
      </span>
    </div>
    <div
      class="ticket-details__item mt-16"
      style="align-items: flex-start">
      <span class="ticket-details__item-label">{{ t('数据源与接收端') }}：</span>
      <span class="ticket-details__item-value">
        <BkTable
          class="subscribe-table"
          :columns="receiverColumns"
          :data="receiverTableData" />
      </span>
    </div>
  </div>

  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('订阅名称') }}：</span>
        <span class="ticket-details__item-value">{{ name }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('Dumper部署位置') }}：</span>
        <span class="ticket-details__item-value">{{ t('集群Master所在主机') }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('数据同步方式') }}：</span>
        <span class="ticket-details__item-value">
          {{ addType === 'incr_sync' ? t('增量同步') : t('全量同步') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    DumperInstallDetails,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<DumperInstallDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    infos,
    clusters,
    name,
    add_type: addType,
  } = props.ticketDetails.details;

  const protocolType = infos[0].protocol_type;

  const subscribeColumns = [
    {
      label: t('DB 名'),
      field: 'db_name',
      width: 300,
    },
    {
      label: t('表名'),
      field: 'table_names',
      minWidth: 100,
      render: ({ data }: {data: { table_names: string[] }}) => (
        <div class="table-names-box">
          {
            data.table_names.map((item, index) => <div key={index} class="name-item">{ item }</div>)
          }
        </div>
      ),
    },
  ];
  const receiverColumns = computed(() => {
    const basicColumns = [
      {
        label: t('数据源集群'),
        field: 'source_cluster_domain',
        showOverflowTooltip: true,
      },
      {
        label: t('部署dumper实例ID'),
        field: 'dumper_id',
        showOverflowTooltip: true,
      },
      {
        label: t('接收端类型'),
        field: 'protocol_type',
        showOverflowTooltip: true,
      },
    ] as {
      label: string,
      field: string,
      showOverflowTooltip?: boolean,
      render?: any
    }[];
    if (protocolType === 'L5_AGENT') {
      const l5Columns = [
        {
          label: 'l5_modid',
          field: 'l5_modid',
        },
        {
          label: 'l5_cmdid',
          field: 'l5_modid',
        },
      ];
      return [...basicColumns, ...l5Columns];
    }
    basicColumns.push({
      label: t('接收端集群与端口'),
      field: 'target_address',
      showOverflowTooltip: true,
      render: ({ data }: {data: DumperInstallDetails['infos'][number]}) => <span>{data.target_address}:{data.target_port}</span>,
    });
    if (protocolType === 'KAFKA') {
      const kafkaColumns = [
        {
          label: t('账号'),
          field: 'kafka_user',
          showOverflowTooltip: true,
        },
        {
          label: t('密码'),
          field: 'kafka_pwd',
          render: ({ data }: {data: DumperInstallDetails['infos'][number]}) => (
            <bk-input
              model-value={data.kafka_pwd}
              disabled
              type="password" />
          ),
        },
      ];
      return [...basicColumns, ...kafkaColumns];
    }
    return basicColumns;
  });

  const subscribeTableMap = props.ticketDetails.details.repl_tables.reduce((results, item) => {
    const [db, table] = item.split('.');
    if (results[db]) {
      results[db].push(table);
    } else {
      // eslint-disable-next-line no-param-reassign
      results[db] = [table];
    }
    return results;
  }, {} as Record<string, string[]>);

  const subscribeTableData = Object.keys(subscribeTableMap).map(item => ({
    db_name: item,
    table_names: subscribeTableMap[item],
  }));

  const receiverTableData = infos.map((item) => {
    const domain = clusters[item.cluster_id].immute_domain;
    return {
      ...item,
      source_cluster_domain: domain,
    };
  });
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';

  .subscribe-table {
    :deep(.table-names-box) {
      display: flex;
      width: 100%;
      flex-wrap: wrap;
      padding-top: 10px;
      padding-bottom: 2px;

      .name-item {
        height: 22px;
        padding: 0 8px;
        margin-right: 4px;
        margin-bottom: 8px;
        line-height: 22px;
        color: #63656e;
        background: #f0f1f5;
        border-radius: 2px;
      }
    }

    :deep(th) {
      .head-text {
        color: #313238;
      }
    }
  }
</style>
