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
  <div class="render-data">
    <RenderTable>
      <RenderTableHeadColumn>
        <span>{{ $t('源集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('集群类型') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('访问密码') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('目标集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn>
        <span>{{ $t('包含Key') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('排除Key') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :required="false"
        :width="120">
        {{ $t('操作') }}
      </RenderTableHeadColumn>
      <template #data>
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-list="clusterList"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';
  import type { SelectItem } from '@views/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';

  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type TableRealRowData,
  } from './Row.vue';

  interface Props {
    clusterList: SelectItem[];
  }

  interface Exposes {
    getValue: () => Promise<TableRealRowData[]>,
    resetTable: () => void
  }


  defineProps<Props>();

  const emits = defineEmits<{
    'change-table-available': [status: boolean]
  }>();

  const tableData = ref([createRowData()]);
  const rowRefs = ref();
  const tableAvailable = computed(() => tableData.value.findIndex(item => Boolean(item.srcCluster)) > -1);


  // 集群域名是否已存在表格的映射表
  const domainMemo = {} as Record<string, boolean>;

  watch(() => tableAvailable.value, (status) => {
    emits('change-table-available', status);
  });

  const handleChangeCluster = async (index: number, domain: string) => {
    tableData.value[index].srcCluster = domain;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all<TableRealRowData[]>(rowRefs.value.map((item: {
      getValue: () => Promise<TableRealRowData>
    }) => item.getValue())),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
<style lang="less">
.render-data {
  .batch-edit-btn {
    margin-left: 4px;
    color: #3a84ff;
    cursor: pointer;
  }
}

</style>
