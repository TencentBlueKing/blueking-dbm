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
      :label="t('订阅的库表')"
      style="flex: 0 0 100%">
      <PrimaryTable
        :data="subscribeTableData"
        ellipsis
        row-key="db_name">
        <TableColumn
          col-key="db_name"
          :title="t('DB 名')" />
        <TableColumn :title="t('表名')">
          <template #default="{ row }: { row: { table_names: string[] } }">
            <div class="table-names-box">
              <div
                v-for="(item, index) in row.table_names"
                :key="index"
                class="name-item">
                {{ item }}
              </div>
            </div>
          </template>
        </TableColumn>
      </PrimaryTable>
    </InfoItem>
    <InfoItem
      :label="t('数据源与接收端')"
      style="flex: 0 0 100%">
      <PrimaryTable
        :data="receiverTableData"
        ellipsis
        row-key="cluster_id">
        <TableColumn
          col-key="source_cluster_domain"
          ellipsis
          :title="t('数据源集群')" />
        <TableColumn
          col-key="dumper_id"
          ellipsis
          :title="t('部署dumper实例ID')" />
        <TableColumn
          col-key="protocol_type"
          :title="t('接收端类型')" />
        <TableColumn :title="t('接收端集群与端口')">
          <template #default="{ row }:{row:RowData}">
            <span>{{ row.target_address }}:{{ row.target_port }}</span>
          </template>
        </TableColumn>
        <template v-if="protocolType === 'L5_AGENT'">
          <TableColumn
            col-key="l5_modid"
            title="l5_modid" />
          <TableColumn
            col-key="l5_cmdid"
            title="l5_cmdid" />
        </template>
        <template v-if="protocolType === 'KAFKA'">
          <TableColumn
            col-key="kafka_user"
            :title="t('账号')" />
          <TableColumn :title="t('密码')">
            <template #default="{ row }:{row:RowData}">
              <BkInput
                disabled
                :model-value="row.kafka_pwd"
                type="password" />
            </template>
          </TableColumn>
        </template>
      </PrimaryTable>
    </InfoItem>
    <InfoItem
      :label="t('订阅名称')"
      style="flex: 0 0 100%">
      {{ name }}
    </InfoItem>
    <InfoItem
      :label="t('Dumper部署位置')"
      style="flex: 0 0 100%">
      {{ t('集群Master所在主机') }}
    </InfoItem>
    <InfoItem
      :label="t('数据同步方式')"
      style="flex: 0 0 100%">
      {{ addType === 'incr_sync' ? t('增量同步') : t('全量同步') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Dumper } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Dumper.Install>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TBINLOGDUMPER_INSTALL,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { add_type: addType, clusters, infos, name } = props.ticketDetails.details;

  const protocolType = infos[0].protocol_type;

  const subscribeTableMap = props.ticketDetails.details.repl_tables.reduce(
    (results, item) => {
      const [db, table] = item.split('.');
      if (results[db]) {
        results[db].push(table);
      } else {
        // eslint-disable-next-line no-param-reassign
        results[db] = [table];
      }
      return results;
    },
    {} as Record<string, string[]>,
  );

  const subscribeTableData = Object.keys(subscribeTableMap).map((item) => ({
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
