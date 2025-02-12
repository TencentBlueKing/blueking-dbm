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
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Es } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Es.Replace>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.ES_REPLACE,
    inheritAttrs: false
  })

  const { t } = useI18n();

  type nodeIpList = {
    key: string,
    value: string[],
  }

  /**
   * 替换
   */

  const columns = [{
    label: t('集群ID'),
    field: 'cluster_id',
    render: ({ cell }: { cell: string }) => <span class="details-replace__cell">{cell || '--'}</span>,
  }, {
    label: t('集群名称'),
    field: 'immute_domain',
    showOverflowTooltip: false,
    render: ({ data }: { data: any }) => data.immute_domain,
  }, {
    label: t('集群类型'),
    field: 'cluster_type_name',
    render: ({ cell }: { cell: string }) => <span class="details-replace__cell">{cell || '--'}</span>,
  }, {
    label: t('角色类型'),
    field: 'new_nodes',
    render: ({ cell }: { cell: nodeIpList[] }) => cell.map((item) => {
      const lineHeight = item.value.length * 30;
      return <p class="details-replace__cell" style={{ 'line-height': `${lineHeight}px` }}>{item.key}</p>;
    }),
  }, {
    label: t('新节点IP'),
    field: 'new_nodes',
    render: ({ cell }: { cell: nodeIpList[] }) => cell.map(item => (
      <div class="details-replace__cell">
        {item.value.map((ip, index) => <p class="details-replace__ip">{ip}
          { index === 0
            ? <i v-bk-tooltips={t('复制 IP')} class="db-icon-copy" onClick={() => handleCopy(item.value)} />
            : '' }
          </p>)}
      </div>
    )),
  }, {
    label: t('被替换的节点IP'),
    field: 'old_nodes',
    render: ({ cell }: { cell: nodeIpList[] }) => cell.map(item => (
      <div class="details-replace__cell">
        {item.value.map((ip, index) => <p class="details-replace__ip">{ip}
          { index === 0
            ? <i v-bk-tooltips={t('复制 IP')} class="db-icon-copy" onClick={() => handleCopy(item.value)} />
            : '' }
          </p>)}
      </div>
    )),
  }];

  const dataList = computed(() => {
    const list: any = [];
    const clusterId = props.ticketDetails?.details?.cluster_id;
    const clusters = props.ticketDetails?.details?.clusters?.[clusterId] || {};
    const newNodes = convertNodeFormat(props.ticketDetails?.details?.new_nodes || {});
    const oldNodes = convertNodeFormat(props.ticketDetails?.details?.old_nodes || {});
    list.push(Object.assign({
      cluster_id: clusterId, new_nodes: newNodes, old_nodes: oldNodes,
    }, clusters));
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
  }
</script>
