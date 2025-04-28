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
  <BkTable
    :data="tableData"
    :merge-cells="mergeCells"
    show-overflow-tooltip>
    <BkTableColumn
      field="ip"
      fixed="left"
      :label="t('待替换的主机')" />
    <BkTableColumn
      field="role"
      :label="t('角色类型')" />
    <BkTableColumn
      field="cluster"
      :label="t('所属集群')" />
    <BkTableColumn
      field="spec"
      :label="t('新机规格')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Cutoff>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_CUTOFF,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  const { clusters, infos, specs } = props.ticketDetails.details;
  const tableData = infos.reduce(
    (results, item) => {
      const types = ['mongo_config', 'mongodb', 'mongos'] as ['mongo_config', 'mongodb', 'mongos'];
      types.forEach((type) => {
        if (item[type].length) {
          const list = item[type].map((obj) => ({
            cluster: clusters[item.cluster_id].immute_domain,
            ip: obj.ip,
            role: type,
            spec: specs[obj.spec_id].name,
          }));
          results.push(...list);
        }
      });
      mergeCells.value.push({
        col: 2,
        colspan: 1,
        row: mergeCells.value.length ? mergeCells.value[mergeCells.value.length - 1].rowspan : 0,
        rowspan: item.mongo_config.length + item.mongodb.length + item.mongos.length,
      });
      return results;
    },
    [] as {
      cluster: string;
      ip: string;
      role: string;
      spec: string;
    }[],
  );
</script>
