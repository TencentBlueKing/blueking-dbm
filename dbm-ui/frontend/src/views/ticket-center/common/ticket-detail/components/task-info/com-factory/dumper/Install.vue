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
    <InfoItem
      :label="t('订阅的库表：')"
      style="flex: 0 0 100%">
      <BkTable
        :columns="subscribeColumns"
        :data="subscribeTableData" />
    </InfoItem>
    <InfoItem
      :label="t('数据源与接收端：')"
      style="flex: 0 0 100%">
      <BkTable
        :columns="receiverColumns"
        :data="receiverTableData" />
    </InfoItem>
    <InfoItem
      :label="t('订阅名称：')"
      style="flex: 0 0 100%">
      {{ name }}
    </InfoItem>
    <InfoItem
      :label="t('Dumper部署位置：')"
      style="flex: 0 0 100%">
      {{ t('集群Master所在主机') }}
    </InfoItem>
    <InfoItem
      :label="t('数据同步方式：')"
      style="flex: 0 0 100%">
      {{ addType === 'incr_sync' ? t('增量同步') : t('全量同步') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, {type Dumper} from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';


  interface Props {
    ticketDetails: TicketModel<Dumper.Install>
  }

  type RowData = Props['ticketDetails']['details']['infos'][number]

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TBINLOGDUMPER_INSTALL,
    inheritAttrs: false
  })

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
      render: ({ data }: {data: RowData}) => <span>{data.target_address}:{data.target_port}</span>,
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
          render: ({ data }: {data: RowData}) => (
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
