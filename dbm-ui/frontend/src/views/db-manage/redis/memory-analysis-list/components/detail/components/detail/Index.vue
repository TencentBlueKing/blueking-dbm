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
      :memory-unsed="listInfo.memoryUnsed" />
    <DbQuickSearch
      v-model="quickSearchValue"
      :data="quickSearchData"
      :placeholder="t('搜索 Key 类型、搜索 Key 模式')"
      style="width: 550px; margin-left: auto"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="table"
      class="mt-16"
      :data-source="getKeyStatDetails"
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
        col-key="key_class"
        :filter="tableFilter?.['key_class']"
        fixed="left"
        :min-width="200"
        :title="t('Key 模式')">
      </TableColumn>
      <TableColumn
        col-key="key_name"
        :min-width="200"
        :title="t('Key 样本')">
      </TableColumn>
      <TableColumn
        col-key="count"
        :title="t('数量')"
        width="100">
      </TableColumn>
      <TableColumn
        col-key="avg_ttl_human"
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
        col-key="min_idletime_show"
        :title="t('最近访问时间')"
        :width="200">
        <template #title>
          <BkPopover placement="bottom">
            <span style="border-bottom: 1px dashed">{{ t('最近访问时间') }}</span>
            <template #content>
              <p>{{ t('1，版本高于6.2时可用，不可用时显示\"-\"') }}</p>
              <p>{{ t('2，不会刷新idletime的命令有：ttl、pttl、object idletime') }}</p>
              <p>
                {{
                  t(
                    '3，共享：值为[0,9999]的key属于"共享对象"。举个例子：如果存在3个值为1的key，访问其中一个key，另外2个的idletime也会被刷新',
                  )
                }}
              </p>
            </template>
          </BkPopover>
        </template>
      </TableColumn>
      <TableColumn
        col-key="avg_key_used_bytes"
        :title="t('单 Key 平均占用内存')"
        :width="160">
        <template #default="{ row }: { row: IRowData }">
          {{ bytePretty(row.avg_key_used_bytes) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="avg_key_length"
        :title="t('平均成员数量')"
        :width="120">
      </TableColumn>
      <TableColumn
        col-key="mem_used_bytes"
        :title="t('占用内存')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ bytePretty(row.mem_used_bytes) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="cpu"
        :title="t('占用内存占比')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          <div class="detail-ratio">
            <BkProgress
              bg-color="#EAEBF0"
              class="mr-8"
              :color="getColor(Number(row.mem_used_pct))"
              :percent="Number(row.mem_used_pct)"
              :show-text="false"
              stroke-linecap="square"
              :stroke-width="14"
              type="circle"
              :width="20" />
            <span class="detail-ratio">{{ row.mem_used_pct }} %</span>
          </div>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getKeyStatDetails } from '@services/source/redisKeystat';

  import DbTable from '@components/db-table/IndexNew.vue';

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

  type IRowData = ServiceReturnType<typeof getKeyStatDetails>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { quickSearchData, quickSearchValue } = useSearchSelect();
  const tableFilter = useTableFilter();

  const tableRef = useTemplateRef('table');

  const detailData = computed(() => tableRef.value?.getData<IRowData>());
  const detailDataLength = computed(() => detailData.value?.length || 0);
  const isLoading = computed(() => tableRef.value?.loading || false);

  const listInfo = computed(() =>
    (detailData.value || []).reduce(
      (prevCount, item) => ({
        count: prevCount.count + item.count,
        memoryUnsed: prevCount.memoryUnsed + item.mem_used_pct,
      }),
      {
        count: 0,
        memoryUnsed: 0,
      },
    ),
  );

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const fetchData = () => {
    tableRef.value!.fetchData({
      ...transfromDataToQuery(quickSearchValue.value),
      record_id: props.recordId,
    });
  };

  const getColor = (ratio: number) => {
    let color = '#2DCB56';

    if (ratio >= 90) {
      color = '#EA3636';
    } else if (ratio >= 70) {
      color = '#FF9C01';
    }
    return color;
  };

  onMounted(() => {
    fetchData();
  });

  defineExpose<Exposes>({
    dataLength: detailDataLength,
    loading: isLoading,
  });
</script>

<style lang="less" scoped>
  .detail-ratio {
    display: flex;
    font-weight: bolder;
    color: #63656e;
  }
</style>
