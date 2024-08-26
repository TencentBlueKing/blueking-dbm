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
  <RenderTable>
    <template #default>
      <RenderTableHeadColumn
        fixed="left"
        :min-width="200"
        :width="250">
        {{ t('目标集群') }}
        <template #append>
          <BatchOperateIcon
            class="ml-4"
            @click="handleShowBatchSelector" />
        </template>
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="190"
        :width="220">
        <template #append>
          <BatchEditColumn
            v-model="isShowBatchEdit"
            :data-list="selectList"
            :title="t('清档类型')"
            @change="handleBatchEdit">
            <BatchOperateIcon
              class="ml-4"
              type="edit"
              @click="handleShowBatchEdit" />
          </BatchEditColumn>
        </template>
        {{ t('清档类型') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="200"
        :width="250">
        {{ t('目标DB名') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="200"
        :width="250">
        {{ t('目标表名') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="200"
        :required="false"
        :width="250">
        {{ t('忽略DB名') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        :min-width="200"
        :required="false"
        :width="250">
        {{ t('忽略表名') }}
      </RenderTableHeadColumn>
      <RenderTableHeadColumn
        fixed="right"
        :required="false"
        :width="100">
        {{ t('操作') }}
      </RenderTableHeadColumn>
    </template>

    <template #data>
      <slot />
    </template>
  </RenderTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@components/batch-edit-column/Index.vue';
  import BatchOperateIcon from '@components/batch-operate-icon/Index.vue';
  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  interface Emits {
    (e: 'batchSelectCluster'): void;
    (e: 'batchEditTruncateType', value: string): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const selectList = [
    {
      value: 'truncate_table',
      label: t('清除表数据_truncatetable'),
    },
    {
      value: 'drop_table',
      label: t('清除表数据和结构_droptable'),
    },
    {
      value: 'drop_database',
      label: t('删除整库_dropdatabase'),
    },
  ];

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = !isShowBatchEdit.value;
  };

  const handleBatchEdit = (value: string) => {
    emits('batchEditTruncateType', value);
  };

  const handleShowBatchSelector = () => {
    emits('batchSelectCluster');
  };
</script>
