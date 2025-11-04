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
  <div>
    <InstanceInfo
      :count="listInfo.count"
      :instace-list="instaceList"
      :memory-unsed="listInfo.memoryUnsed"
      @change="handleShowChange" />
    <DbQuickSearch
      v-model="quickSearchValue"
      :data="quickSearchData"
      :placeholder="t('搜索 Key 类型、搜索 Key 样本')"
      style="width: 550px; margin-left: auto"
      @change="handleQuickSearchChange" />
    <div ref="tableContainer">
      <PrimaryTable
        class="mt-16"
        :data="rankData"
        :loading="isLoading"
        :max-height="tableMaxHeight"
        row-key="key_name"
        @filter-change="handleFilterChange">
        <TableColumn
          col-key="key_type"
          :filter="tableFilter?.['key_type']"
          fixed="left"
          :title="t('Key 类型')"
          :width="100">
        </TableColumn>
        <TableColumn
          col-key="key_name"
          :filter="tableFilter?.['key_name']"
          fixed="left"
          :min-width="200"
          :title="t('Key 样本')">
        </TableColumn>
        <TableColumn
          col-key="ttl_human"
          :title="t('过期时间')"
          :width="200">
          <template #title>
            <BkPopover placement="bottom">
              <span style="border-bottom: 1px dashed">{{ t('过期时间') }}</span>
              <template #content>
                <p>{{ t('不过期： 表示全部不过期') }}</p>
                <p>{{ t('平均：2.0day： 表示全部都有过期，平均过期时间为2.0day') }}</p>
                <p>{{ t('数量：33857,平均:1.9day：表示有过期的数量33857(不是全部），平均过期时间为1.9day') }}</p>
              </template>
            </BkPopover>
          </template>
        </TableColumn>
        <TableColumn
          col-key="key_length"
          :title="t('Key 长度')"
          :width="100">
        </TableColumn>
        <TableColumn
          col-key="value_size"
          :title="t('Value 长度')"
          :width="140">
          <template #default="{ row }: { row: IRowData }">
            {{ bytePretty(row.value_size) }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="member"
          :title="t('成员数量')"
          :width="100">
        </TableColumn>
        <TableColumn
          col-key="member_len"
          :title="t('成员平均长度')"
          :width="120">
        </TableColumn>
        <TableColumn
          col-key="memory_size"
          :title="t('内存占用')"
          :width="140">
          <template #default="{ row }: { row: IRowData }">
            {{ bytePretty(row.memory_size) }}
          </template>
        </TableColumn>
      </PrimaryTable>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getKeystatRank } from '@services/source/redisKeystat';

  import { useTableMaxHeight } from '@hooks';

  import { bytePretty, transfromDataToQuery } from '@utils';

  import InstanceInfo from '../common/InstanceInfo.vue';

  import useSearchSelect from './useSearchSelect';
  import useTableFilter from './useTableFilter';

  interface Props {
    instaceList: string[];
    recordId: number;
  }

  interface Exposes {
    dataLength: Ref<number>;
    loading: Ref<boolean>;
  }

  type IRowData = ServiceReturnType<typeof getKeystatRank>[number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { quickSearchData, quickSearchValue } = useSearchSelect();
  const tableFilter = useTableFilter();

  const tableContainerRef = useTemplateRef('tableContainer');
  const occupiedHeight = ref(0);
  const tableMaxHeight = useTableMaxHeight(occupiedHeight);

  const dataLength = computed(() => rankData.value?.length || 0);
  const listInfo = computed(() =>
    (rankData.value || []).reduce(
      (prevCount, item) => ({
        count: prevCount.count + item.member,
        memoryUnsed: prevCount.memoryUnsed + item.memory_size,
      }),
      {
        count: 0,
        memoryUnsed: 0,
      },
    ),
  );

  const {
    data: rankData,
    loading: isLoading,
    run: runGetKeystatRank,
  } = useRequest(getKeystatRank, {
    manual: true,
  });

  const calcOccupiedHeight = () => {
    const { top } = tableContainerRef.value!.getBoundingClientRect();
    occupiedHeight.value = top + 18;
  };

  const handleShowChange = () => {
    calcOccupiedHeight();
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const fetchData = () => {
    runGetKeystatRank({
      ...transfromDataToQuery(quickSearchValue.value),
      record_id: props.recordId,
    });
  };

  onMounted(() => {
    calcOccupiedHeight();
    fetchData();
  });

  defineExpose<Exposes>({
    dataLength: dataLength,
    loading: isLoading,
  });
</script>
