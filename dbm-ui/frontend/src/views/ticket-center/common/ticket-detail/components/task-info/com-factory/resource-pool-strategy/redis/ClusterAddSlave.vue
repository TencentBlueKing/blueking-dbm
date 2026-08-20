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
  <TicketInfoTable
    :data="tableData"
    row-key="slaveIp">
    <TicketInfoTableColumn
      col-key="slaveIp"
      :get-copy-value="(row: RowData) => row.slaveIp"
      :title="t('待重建从库主机')" />
    <TicketInfoTableColumn
      col-key="hostIp"
      :title="t('关联主库主机')" />
    <TicketInfoTableColumn
      col-key="clusterName"
      :title="t('所属集群')" />
    <TicketInfoTableColumn
      col-key="sepcName"
      :title="t('规格需求')" />
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.labelNames.length">
          <DbTag
            v-for="item in row.labelNames"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="targetNum"
      :title="t('新增从库主机数量')" />
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ClusterAddSlave>;
  }

  interface RowData {
    clusterName: string;
    clusterType: string;
    hostIp: string;
    labelNames: string[];
    sepcName: string;
    slaveIp: string;
    targetNum: number;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;

  const tableData = infos.reduce((results, item) => {
    item.pairs.forEach((pair) => {
      const specInfo = specs[pair.redis_slave?.spec_id || Object.values(item.resource_spec)[0].spec_id];
      const obj = {
        clusterName: item.cluster_id
          ? clusters[item.cluster_id].immute_domain // 兼容旧单据
          : item.cluster_ids.map((id) => clusters[id].immute_domain).join(','),
        clusterType: clusters[item.cluster_ids[0]].cluster_type,
        hostIp: pair.redis_master.ip,
        labelNames: Object.values(item.resource_spec)[0].label_names || [],
        sepcName: specInfo ? specInfo.name : '--',
        slaveIp: pair.redis_slave?.old_slave_ip || pair.redis_slave.ip,
        targetNum: Object.values(item.resource_spec)[0].count,
      };
      results.push(obj);
    });
    return results;
  }, [] as RowData[]);
</script>
