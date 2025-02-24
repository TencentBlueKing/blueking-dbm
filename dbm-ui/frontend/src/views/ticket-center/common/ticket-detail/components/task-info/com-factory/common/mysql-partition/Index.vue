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
  <DbOriginalTable
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Mysql.Partition>;
  }

  interface RowData {
    action: string[];
    clusterName: string;
    dbName: string;
    ip: string;
    tbName: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      field: 'clusterName',
      label: t('集群'),
      showOverflowTooltip: true,
    },
    {
      field: 'ip',
      label: 'IP',
      showOverflowTooltip: true,
    },
    {
      field: 'dbName',
      label: t('DB 名'),
      showOverflowTooltip: true,
    },
    {
      field: 'tbName',
      label: t('表名'),
      showOverflowTooltip: true,
    },
    {
      field: 'action',
      label: t('分区动作'),
      render: ({ data }: { data: RowData }) => data.action.map((item) => <bk-tag>{item}</bk-tag>),
      showOverflowTooltip: true,
    },
  ];

  const tableData = props.ticketDetails.details.infos.reduce((results, item) => {
    const partitionObjects = item.partition_objects;
    if (partitionObjects.length > 0) {
      partitionObjects.forEach((partion) => {
        if (partion.execute_objects.length > 0) {
          partion.execute_objects.forEach((exeObject) => {
            const action: string[] = [];
            if (exeObject.init_partition.length > 0) {
              action.push(t('初始化分区'));
            }
            if (exeObject.add_partition.length > 0) {
              action.push(t('增加分区'));
            }
            if (exeObject.drop_partition.length > 0) {
              action.push(t('删除分区'));
            }
            const obj = {
              action,
              clusterName: item.immute_domain,
              dbName: exeObject.dblike,
              ip: partion.ip,
              tbName: exeObject.tblike,
            };
            results.push(obj);
          });
        }
      });
    }
    return results;
  }, [] as RowData[]);
</script>
