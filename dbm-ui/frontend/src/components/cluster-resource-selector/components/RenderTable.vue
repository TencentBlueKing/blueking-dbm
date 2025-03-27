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
  <div class="cluster-resource-selector-render-table">
    <DbSearchSelect
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData" />
    <DbTable
      ref="table"
      :data-source="dataSource"
      :height="580"
      ignore-biz
      primary-key="id"
      selectable
      :selected="selected"
      show-select-all-page
      @column-filter="handleFilter"
      @selection="handleSelect">
      <BkTableColumn
        field="master_domain"
        :label="t('目标集群')"
        :min-width="240" />
      <BkTableColumn
        field="cluster_type_name"
        :label="t('集群类型')"
        :min-width="120" />
      <BkTableColumn
        field="phase"
        :filter="filterOption.status"
        :label="t('状态')"
        :min-width="120">
        <template #default="{ data }">
          <DbStatus
            v-if="data.phase === 'online'"
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
        :label="t('所属业务')"
        :min-width="120">
        <template #default="{ data }">
          {{ getBizInfoById(data.bk_biz_id)?.name || '--' }}
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getGlobalCluster } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import { getSearchSelectorParams } from '@utils';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];
  type Parameters = ServiceParameters<typeof getGlobalCluster>;
  export type IValue = ServiceReturnType<typeof getGlobalCluster>['results'][0];

  interface Props {
    params: Parameters;
  }

  const props = defineProps<Props>();

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();

  const searchSelectData = [
    {
      id: 'master_domain',
      name: t('域名'),
    },
  ];

  const filterOption: Record<
    string,
    {
      checked: string[];
      key: string;
      list: { text: string; value: string }[];
    }
  > = {
    status: {
      checked: [],
      key: 'status',
      list: [
        {
          text: t('正常'),
          value: 'running',
        },
        {
          text: t('异常'),
          value: 'unavailable',
        },
      ],
    },
  };

  const searchSelectValue = ref<NonNullable<SearchSelectProps['modelValue']>>([]);
  const dbTableRef = useTemplateRef('table');

  watchEffect(() => {
    dbTableRef.value?.fetchData(getSearchSelectorParams(searchSelectValue.value), props.params);
  });

  const dataSource = (params: Parameters) =>
    getGlobalCluster({
      ...props.params,
      ...params,
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
  .cluster-resource-selector-render-table {
    padding: 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
