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
  <BkTable :data="tableData">
    <BkTableColumn
      field="slaveIp"
      :label="t('待重建从库主机')" />
    <BkTableColumn
      field="hostIp"
      :label="t('关联主库主机')" />
    <BkTableColumn
      field="clusterName"
      :label="t('所属集群')" />
    <BkTableColumn
      field="sepcName"
      :label="t('规格需求')" />
    <BkTableColumn
      field="targetNum"
      :label="t('新增从库主机数量')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterAddSlave>;
  }

  interface RowData {
    clusterName: string;
    clusterType: string;
    hostIp: string;
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
      const specInfo = specs[pair.redis_slave.spec_id];
      const obj = {
        clusterName: item.cluster_id
          ? clusters[item.cluster_id].immute_domain // 兼容旧单据
          : item.cluster_ids.map((id) => clusters[id].immute_domain).join(','),
        clusterType: clusters[item.cluster_ids[0]].cluster_type,
        hostIp: pair.redis_master.ip,
        sepcName: specInfo ? specInfo.name : '--',
        slaveIp: pair.redis_slave.old_slave_ip,
        targetNum: pair.redis_slave.count,
      };
      results.push(obj);
    });
    return results;
  }, [] as RowData[]);
</script>
