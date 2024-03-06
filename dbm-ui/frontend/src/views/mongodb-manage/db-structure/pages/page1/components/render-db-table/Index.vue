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
  <DbFormItem
    :label="t('库表设置')"
    property="charset">
    <div class="render-data">
      <RenderTable>
        <template #default>
          <RenderTableHeadColumn
            :min-width="200"
            :width="200">
            {{ t('构造DB名') }}
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :min-width="200"
            :required="false"
            :width="200">
            {{ t('忽略DB名') }}
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :min-width="200"
            :width="200">
            {{ t('构造表名') }}
          </RenderTableHeadColumn>
          <RenderTableHeadColumn
            :min-width="200"
            :required="false"
            :width="200">
            {{ t('忽略表名') }}
          </RenderTableHeadColumn>
        </template>

        <template #data>
          <RenderDataRow
            v-for="item in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item" />
        </template>
      </RenderTable>
    </div>
  </DbFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './Row.vue';

  interface Exposes {
    getValue: () => any
  }

  const { t } = useI18n();

  const rowRefs = ref();

  const tableData = shallowRef<Array<IDataRow>>([createRowData()]);

  defineExpose<Exposes>({
    async getValue() {
      const infos = await Promise.all(rowRefs.value.map((item: {
        getValue: () => Promise<any>
      }) => item.getValue()));
      return infos[0];
    } });

</script>
<style lang="less">
  .render-data {
    display: block;

    .batch-edit-btn {
      display: inline-block;
      margin-left: 4px;
      line-height: 40px;
      color: #3a84ff;
      vertical-align: top;
      cursor: pointer;
    }
  }
</style>
