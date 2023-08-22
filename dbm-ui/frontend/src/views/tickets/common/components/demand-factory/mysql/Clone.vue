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
    class="details-clone__table"
    :columns="renderColumns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type {
    MySQLCloneDetails,
    TicketDetails,
  } from '@services/types/ticket';

  import { useCopy } from '@hooks';

  interface Props {
    ticketDetails: TicketDetails<MySQLCloneDetails>
  }

  const props = defineProps<Props>();

  const copy = useCopy();

  const { t } = useI18n();

  type cloneItem = {
    source: string,
    target: [],
    module: string,
    cluster_domain: '',
  }

  const isModule = ref(false);

  // 客户端克隆
  const columns = [{
    label: t('源客户端IP'),
    field: 'source',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('所属模块'),
    field: 'module',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: cell,
          allowHTML: true,
      }}>
        <span>{cell}</span>
      </div>
    ),
  }, {
    label: t('新客户端IP'),
    field: 'target',
    render: ({ cell }: { cell: [] }) => cell.map((ip, index) => <p class="pt-2 pb-2">{ip}
      { index === 0
        ? <i v-bk-tooltips={t('复制IP')} class="db-icon-copy" onClick={() => copy(cell.join('\n'))} />
        : '' }
    </p>),
  }];

  // 实例克隆
  const instanceColumns = [{
    label: t('源实例'),
    field: 'source',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('所属集群'),
    field: 'cluster_domain',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: cell,
          allowHTML: true,
      }}>
        <span>{cell}</span>
      </div>
    ),
  }, {
    label: t('新实例'),
    field: 'target',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }];

  const renderColumns = computed(() => {
    if (isModule.value) {
      return columns;
    }
    return instanceColumns;
  });

  const dataList = computed(() => {
    const list: cloneItem[] = [];
    const cloneData = props.ticketDetails?.details?.clone_data || [];
    cloneData.forEach((item) => {
      const { source, target, module, cluster_domain: clusterDomain } = item;
      if (clusterDomain) {
        isModule.value = false;
        list.push(Object.assign({ source, target, cluster_domain: clusterDomain }));
      } else if (module) {
        isModule.value = true;
        list.push(Object.assign({ source, target, module }));
      }
    });
    return list;
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
