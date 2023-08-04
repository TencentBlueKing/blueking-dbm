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
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('关联单据') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('源集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="200"
        :required="false"
        :width="200">
        <span>{{ $t('源实例') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('目标集群') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('包含Key') }}</span>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn :required="false">
        <span>{{ $t('排除Key') }}</span>
      </RenderTableHeadColumn>
      <template #data>
        <RenderDataRow
          v-for="item in tableData"
          :key="item.billId"
          ref="rowRefs"
          :data="item" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@views/redis/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/redis/common/render-table/Index.vue';

  import RenderDataRow, {
    type IDataRow,
    type InfoItem,
  } from './Row.vue';

  interface Props {
    tableData: IDataRow[]
  }

  interface Exposes {
    getValue: () => Promise<InfoItem[]>
  }

  defineProps<Props>();


  const rowRefs = ref();


  defineExpose<Exposes>({
    getValue: () => Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue())),
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
