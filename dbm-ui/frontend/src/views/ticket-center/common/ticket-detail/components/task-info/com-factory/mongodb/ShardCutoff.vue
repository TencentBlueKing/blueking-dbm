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
  <PrimaryTable
    :data="tableData"
    row-key="ip"
    :rowspan-and-colspan="rowspanAndColspan">
    <TableColumn
      col-key="ip"
      fixed="left"
      :title="t('待替换的主机')" />
    <TableColumn
      col-key="role"
      :title="t('角色类型')" />
    <TableColumn
      col-key="cluster"
      :title="t('所属集群')" />
    <TableColumn
      col-key="spec"
      :title="t('新机规格')" />
    <TableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: { label_names: string[] } }">
        <template v-if="row.label_names?.length">
          <BkTag
            v-for="item in row.label_names"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <BkTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </BkTag>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ShardCutoff>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_SHARD_CUTOFF,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const spanInfo: {
    rowIndex: number;
    rowspan: number;
  }[] = [];
  const { clusters, infos, specs } = props.ticketDetails.details;
  const tableData = infos.reduce(
    (results, item) => {
      const types = ['mongo_config', 'mongodb', 'mongos'] as ['mongo_config', 'mongodb', 'mongos'];
      types.forEach((type) => {
        if (item[type] && item[type].length) {
          const list = item[type].map((obj) => ({
            cluster: clusters[item.cluster_id].immute_domain,
            ip: obj.ip,
            label_names: Object.values(item.resource_spec)[0].label_names,
            role: type,
            spec: specs[Object.values(item.resource_spec)[0].spec_id].name,
          }));
          results.push(...list);
        }
      });
      spanInfo.push({
        rowIndex: spanInfo.length ? spanInfo[spanInfo.length - 1].rowspan : 0,
        rowspan: item.mongo_config.length + item.mongodb.length + item.mongos.length,
      });
      return results;
    },
    [] as {
      cluster: string;
      ip: string;
      label_names: string[];
      role: string;
      spec: string;
    }[],
  );

  const rowspanAndColspan = ({ colIndex, rowIndex }: { colIndex: number; rowIndex: number }) => {
    const spanItem = spanInfo.find((item) => colIndex === 2 && item.rowIndex === rowIndex);
    if (spanItem) {
      return {
        rowspan: spanItem.rowspan,
      };
    }
    return {};
  };
</script>
