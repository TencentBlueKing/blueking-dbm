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

  import type { SpiderPartitionManageDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderPartitionManageDetails>
  }

  interface RowData {
    clusterName: string,
    ip: string,
    dbName: string,
    tbName: string,
    action: string[],
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: 'IP',
      field: 'ip',
      showOverflowTooltip: true,
    },
    {
      label: t('DB 名'),
      field: 'dbName',
      showOverflowTooltip: true,
    },
    {
      label: t('表名'),
      field: 'tbName',
      showOverflowTooltip: true,
    },
    {
      label: t('分区动作'),
      field: 'action',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => data.action.map(item => (
        <bk-tag>{ item }</bk-tag>
      )),
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
              clusterName: item.immute_domain,
              ip: partion.ip,
              dbName: exeObject.dblike,
              tbName: exeObject.tblike,
              action,
            };
            results.push(obj);
          });
        }
      });
    }
    return results;
  }, [] as RowData[]);
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
