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

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Cutoff>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_CUTOFF,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;

  const columns = [
    {
      label: t('待替换的主机'),
      field: 'ip',
      showOverflowTooltip: true,
    },
    {
      label: t('角色类型'),
      field: 'role',
    },
    {
      label: t('所属集群'),
      field: 'cluster',
      showOverflowTooltip: true,
    },
    {
      label: t('新机规格'),
      field: 'spec',
      showOverflowTooltip: true,
    },
  ];

  const tableData = infos.reduce(
    (results, item) => {
      const types = ['mongo_config', 'mongodb', 'mongos'] as ['mongo_config', 'mongodb', 'mongos'];
      types.forEach((type) => {
        if (item[type].length) {
          const list = item[type].map((obj) => ({
            ip: obj.ip,
            role: type,
            cluster: clusters[item.cluster_id].immute_domain,
            spec: specs[obj.spec_id].name,
          }));
          results.push(...list);
        }
      });
      return results;
    },
    [] as {
      ip: string;
      role: string;
      cluster: string;
      spec: string;
    }[],
  );
</script>
