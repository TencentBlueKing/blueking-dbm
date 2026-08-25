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
  <DBCollapseTable
    class="mt-16"
    :operations="operations"
    :table-props="tableData">
    <template #title>
      【白名单】
      <span class="pr-4">- 共 </span>
      <span v-if="totals.ipNums > 0">
        <span class="bk-ip-selector-number">{{ totals.ipNums }}</span>
        台
      </span>
      <span v-if="totals.symbolNums > 0">
        <template v-if="totals.ipNums > 0 && totals.symbolNums > 0">，</template>
        <span class="bk-ip-selector-number">{{ totals.symbolNums }}</span>
        个通配
      </span>
    </template>
  </DBCollapseTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getWhitelist } from '@services/source/whitelist';

  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';
  import RenderRow from '@components/render-row/index.vue';
  import type { PrimaryTableCol } from '@components/tdesign-ui/table';

  import { execCopy } from '@utils';

  type WhitelistItem = ServiceReturnType<typeof getWhitelist>['results'][number];

  interface Props {
    data: WhitelistItem[];
    search: string;
  }

  interface Emits {
    (e: 'clearSelected'): void;
    (e: 'removeSelected', index: number): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const totals = computed(() => {
    const ips = props.data.reduce((result, item) => result.concat(item.ips || []), [] as string[]);
    const uniqueIps = [...new Set(ips)];
    const symbolNums = uniqueIps.filter((ip) => ip.endsWith('%')).length;

    return {
      ipNums: uniqueIps.length - symbolNums,
      symbolNums,
    };
  });

  const renderData = computed(() => {
    if (!props.search) return props.data;
    return props.data.filter((item) => item.ips.some((ip) => ip.includes(props.search)));
  });

  const columns: PrimaryTableCol[] = [
    {
      cell: (_, { row }) => <RenderRow data={row.ips} />,
      colKey: 'ips',
      ellipsis: false,
      title: 'IP',
    },
    {
      colKey: 'remark',
      title: t('备注'),
    },
    {
      cell: (_, { rowIndex }) => (
        <bk-button
          text
          theme='primary'
          onClick={() => handleRemoveSelected(rowIndex)}>
          {t('删除')}
        </bk-button>
      ),
      colKey: 'operation',
      title: t('操作'),
      width: 100,
    },
  ];

  const tableData = computed(() => ({
    columns,
    data: renderData.value,
    maxHeight: 474,
  }));

  // IP 操作
  const operations = [
    {
      label: t('清除所有'),
      onClick: handleClearSelected,
    },
    {
      label: t('复制'),
      onClick: () => {
        const ips = props.data.reduce((result: string[], item: WhitelistItem) => result.concat(item.ips), []);
        execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
      },
    },
  ];

  function handleRemoveSelected(index: number) {
    emits('removeSelected', index);
  }

  function handleClearSelected() {
    emits('clearSelected');
  }
</script>
