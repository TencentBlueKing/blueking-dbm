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
  <div class="render-table">
    <DbSearchSelect
      v-model="searchSelectValue"
      class="mb-12"
      :data="searchSelectData" />
    <DbTable
      ref="table"
      :data-source="dataSource"
      :height="500"
      ignore-biz
      primary-key="instance_address"
      selectable
      :selected="selected"
      show-select-all-page
      @column-filter="handleFilter"
      @selection="updateLastValues">
      <BkTableColumn
        field="instance_address"
        :label="instanceRoleText"
        :min-width="150" />
      <BkTableColumn
        field="role"
        :label="t('角色类型')"
        :min-width="100" />
      <BkTableColumn
        field="status"
        :filter="filterOption.status"
        :label="t('状态')"
        :min-width="120">
        <template #default="{ data }">
          <DbStatus
            v-if="data.status === 'running'"
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
        field="master_domain"
        :label="t('所属集群')"
        :min-width="220" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getGlobalInstance } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';

  import type { SearchValue } from '@components/vue2/search-select/index.vue';

  import { getSearchSelectorParams } from '@utils';

  type IValue = ServiceReturnType<typeof getGlobalInstance>['results'][0];

  interface Props {
    params?: ServiceParameters<typeof getGlobalInstance>;
    selected: IValue[];
  }

  type Emits = (e: 'change', value: Props['selected']) => void;

  const props = withDefaults(defineProps<Props>(), {
    params: () => ({
      cluster_types: [ClusterTypes.TENDBHA],
      instance_inner_role: 'master',
    }),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const searchSelectData = [
    {
      id: 'instance',
      name: 'IP:Port',
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
    // role: {
    //   key: 'instance_inner_role',
    //   checked: [],
    //   list: [
    //     {
    //       text: 'master',
    //       value: 'master',
    //     },
    //     {
    //       text: 'slave',
    //       value: 'slave',
    //     },
    //   ].filter((item) => item.value === props.params.instance_inner_role),
    // },
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

  // 首字母大写
  const capitalize = (str: string) => str.toLowerCase().replace(/^\w/, (match) => match.toUpperCase());

  const instanceRoleText = t('xx实例', { role: capitalize(props.params?.instance_inner_role || 'master') });
  const searchSelectValue = ref<SearchValue[]>([]);
  const dbTableRef = useTemplateRef('table');

  watchEffect(() => {
    dbTableRef.value?.fetchData(getSearchSelectorParams(searchSelectValue.value), props.params);
  });

  const dataSource = (params: Props['params']) =>
    getGlobalInstance({
      ...props.params,
      ...params,
    });

  const handleFilter = ({ checked, field }: { checked: string[]; field: string }) => {
    dbTableRef.value?.fetchData({
      [filterOption[field].key]: checked.join(','),
    });
  };

  const updateLastValues = (instances: string[], rows: IValue[]) => {
    const otherBizItems = props.selected.filter(
      (item) => props.params.bk_biz_id && item.bk_biz_id !== props.params.bk_biz_id,
    );
    emits('change', [...otherBizItems, ...rows]);
  };
</script>

<style lang="less">
  .render-table {
    padding: 0 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
