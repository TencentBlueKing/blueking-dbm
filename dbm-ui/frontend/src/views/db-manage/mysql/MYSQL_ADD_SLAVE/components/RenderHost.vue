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
  <EditableTableColumn
    field="slave.ip"
    :label="t('新主从主机')"
    :min-width="300"
    required>
    <EditableTableBlock
      v-model="modelValue.ip"
      :placeholder="t('请选择主机')">
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableTableBlock>
  </EditableTableColumn>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    :multiple="false"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { Block as EditableTableBlock, Column as EditableTableColumn } from '@components/editable-table/Index.vue';
  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  const modelValue = defineModel<IValue>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (hostInfo: IValue[]) => {
    [modelValue.value] = hostInfo;
  };
</script>

<style lang="less" scoped>
  :deep(.select-icon) {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
