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
    :data="dataList">
    <TableColumn
      col-key="cluster_id"
      :title="t('集群ID')">
      <template #default="{ row }">
        <span class="details-replace__cell">{{ row.cluster_id || '--' }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="immute_domain"
      :ellipsis="false"
      :title="t('集群名称')">
      <template #default="{ row }">
        <div
          v-overflow-tips="{
            allowHTML: true,
            content: `
            <p>${t('域名')}：${row.immute_domain}</p>
            ${row.name ? `<p>${t('集群别名')}：${row.name}</p>` : ''}
          `,
          }"
          class="details-replace__cell text-overflow">
          <span>{{ row.immute_domain }}</span>
          <br />
          <span class="cluster-name__alias">{{ row.name }}</span>
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_type_name"
      :title="t('集群类型')">
      <template #default="{ row }">
        <span class="details-replace__cell">{{ row.cluster_type_name || '--' }}</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="new_nodes_type"
      :title="t('角色类型')">
      <template #default="{ row }">
        <p
          v-for="(item, index) in row.new_nodes"
          :key="index"
          class="details-replace__cell"
          :style="{ lineHeight: item.value.length * 30 + 'px' }">
          {{ item.key }}
        </p>
      </template>
    </TableColumn>
    <TableColumn
      col-key="new_nodes_ip"
      :title="t('新节点IP')">
      <template #default="{ row }">
        <div
          v-for="(item, itemIndex) in row.new_nodes"
          :key="itemIndex"
          class="details-replace__cell">
          <p
            v-for="(ip, ipIndex) in item.value"
            :key="ipIndex"
            class="details-replace__ip">
            {{ ip }}
            <i
              v-if="ipIndex === 0"
              v-bk-tooltips="t('复制 IP')"
              class="db-icon-copy"
              @click="handleCopy(item.value)" />
          </p>
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="old_nodes_ip"
      :title="t('被替换的节点IP')">
      <template #default="{ row }">
        <div
          v-for="(item, itemIndex) in row.old_nodes"
          :key="itemIndex"
          class="details-replace__cell">
          <p
            v-for="(ip, ipIndex) in item.value"
            :key="ipIndex"
            class="details-replace__ip">
            {{ ip }}
            <i
              v-if="ipIndex === 0"
              v-bk-tooltips="t('复制 IP')"
              class="db-icon-copy"
              @click="handleCopy(item.value)" />
          </p>
        </div>
      </template>
    </TableColumn>
  </DbOriginalTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Pulsar } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Pulsar.Replace>;
  }

  defineOptions({
    name: TicketTypes.PULSAR_REPLACE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  type nodeIpList = {
    key: string;
    value: string[];
  };

  const dataList = computed(() => {
    const list: any = [];
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};
    const newNodes = convertNodeFormat(props.ticketDetails?.details?.new_nodes || {});
    const oldNodes = convertNodeFormat(props.ticketDetails?.details?.old_nodes || {});
    list.push(
      Object.assign(
        {
          cluster_id: clusterId,
          new_nodes: newNodes,
          old_nodes: oldNodes,
        },
        clusters,
      ),
    );
    return list;
  });

  // 获取节点IP列表
  function convertNodeFormat(obj: Props['ticketDetails']['details']['new_nodes']) {
    const nodeList: any = [];
    Object.entries(obj).forEach((item) => {
      const key = item[0];
      const value = item[1];
      if (value.length) {
        const data = value.map((key: any) => key.ip);
        nodeList.push({ key, value: data });
      }
    });
    return nodeList;
  }

  const handleCopy = (value: nodeIpList['value']) => {
    execCopy(value.join('\n'), t('复制成功，共n条', { n: value.length }));
  };
</script>
