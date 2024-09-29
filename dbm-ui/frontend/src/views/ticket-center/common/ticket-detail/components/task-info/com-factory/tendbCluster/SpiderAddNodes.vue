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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('扩容节点类型')">
      <template #default="{ data }: { data: RowData }">
        {{ data.add_spider_role }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('规格')"
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        {{ specInfoMap[data.resource_spec.spider_ip_list.spec_id]?.spec_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('扩容数量')">
      <template #default="{ data }: { data: RowData }">
        {{ data.resource_spec.spider_ip_list.count }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { DBTypes, TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.SpiderAddNodes>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const specInfoMap = shallowRef<Record<number, ResourceSpecModel>>({});

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: DBTypes.TENDBCLUSTER,
        limit: -1,
        offset: 0,
      },
    ],
    onSuccess(data) {
      specInfoMap.value = data.results.reduce(
        (result, item) =>
          Object.assign(result, {
            [item.spec_id]: item,
          }),
        {},
      );
    },
  });
</script>
