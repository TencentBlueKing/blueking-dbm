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
  <div class="resource-selector-render-table">
    <DbSearchSelect
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData" />
    <DbTable
      ref="table"
      :data-source="dataSource"
      :height="550"
      primary-key="ip"
      selectable
      :selected="selected"
      show-select-all-page
      @column-filter="handleFilter"
      @selection="handleSelect">
      <BkTableColumn
        field="ip"
        label="IP"
        :min-width="120" />
      <BkTableColumn
        field="instance_role"
        :filter="filterOption.instance_role"
        :label="t('角色类型')"
        :min-width="120" />
      <BkTableColumn
        field="bk_cloud_name"
        :label="t('云区域')"
        :min-width="100" />
      <BkTableColumn
        :label="t('Agent 状态')"
        :min-width="120">
        <template #default="{ data }">
          <DbStatus
            v-if="data.host_info?.alive === 1"
            theme="success">
            {{ t('正常') }}
          </DbStatus>
          <DbStatus
            v-else
            theme="danger">
            {{ t('异常') }}
          </DbStatus>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="cluster_type_name"
        :label="t('架构类型')"
        :min-width="120" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getRedisMachineList } from '@services/source/redis';

  import { getSearchSelectorParams } from '@utils';

  import { type TopoTreeNode } from './TopoTree.vue';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];
  type Parameters = ServiceParameters<typeof getRedisMachineList>;
  export type IValue = ServiceReturnType<typeof getRedisMachineList>['results'][0];

  interface Props {
    node?: TopoTreeNode;
  }

  const props = defineProps<Props>();

  const selected = defineModel<Partial<IValue>[]>('selected', {
    required: true,
  });

  const { t } = useI18n();

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
  ];

  const filterOption: Record<
    string,
    {
      checked: string[];
      key: string;
      list: { text: string; value: string | number }[];
    }
  > = {
    instance_role: {
      checked: [],
      key: 'instance_role',
      list: [
        {
          text: 'redis_master',
          value: 'redis_master',
        },
        {
          text: 'redis_slave',
          value: 'redis_slave',
        },
        {
          text: 'proxy',
          value: 'proxy',
        },
      ],
    },
  };

  const searchSelectValue = ref<NonNullable<SearchSelectProps['modelValue']>>([]);
  const dbTableRef = useTemplateRef('table');

  watchEffect(() => {
    dbTableRef.value?.fetchData(getSearchSelectorParams(searchSelectValue.value), {
      cluster_ids: props.node?.obj === 'cluster' ? `${props.node.id}` : undefined,
    });
  });

  const dataSource = (params: Parameters) =>
    getRedisMachineList({
      ...params,
      cluster_ids: props.node?.obj === 'cluster' ? `${props.node.id}` : undefined,
    });

  const handleFilter = ({ checked, field }: { checked: string[]; field: string }) => {
    dbTableRef.value?.fetchData({
      [filterOption[field].key]: checked.join(','),
    });
  };

  const handleSelect = (_values: string[], rows: IValue[]) => {
    selected.value = rows;
  };
</script>

<style lang="less">
  .resource-selector-render-table {
    padding: 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
