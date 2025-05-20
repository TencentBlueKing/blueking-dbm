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
  <BkResizeLayout
    :border="false"
    collapsible
    initial-divide="340px"
    :max="420"
    :min="320">
    <template #aside>
      <ManualInputPanel
        :params="params"
        @change="handleChangeParams" />
    </template>
    <template #main>
      <RenderTable
        :params="localParams"
        :selected="selected"
        @change="handleChange" />
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import ManualInputPanel from './components/ManualInputPanel.vue';
  import RenderTable, { type IValue, type Parameters } from './components/RenderTable.vue';

  interface Props {
    params: {
      cluster_type: string;
      db_type: DBTypes;
      role: string;
    };
  }

  const props = defineProps<Props>();

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const localParams = ref<Parameters>({
    db_type: DBTypes.MYSQL,
  });

  const handleChangeParams = (params: { bk_biz_id?: number; db_module_id?: number; instance?: string }) => {
    localParams.value = {
      ...props.params,
      ...params,
    };
  };

  const handleChange = (data: IValue[]) => {
    selected.value = data;
  };
</script>
