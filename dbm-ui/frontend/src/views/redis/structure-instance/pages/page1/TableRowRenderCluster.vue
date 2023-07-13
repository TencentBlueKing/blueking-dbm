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
  <div class="first-column">
    <BkPopover
      v-if="isDestroing"
      theme="light">
      <BkCheckbox
        :disabled="isDestroied || isDestroing"
        :model-value="modelValue"
        style="margin-right:8px;vertical-align: middle;"
        @change="(value: boolean) => handleSelectChange(value, data)"
        @click="(e: Event) => e.stopPropagation()" />
      <template #content>
        <span>销毁任务正在进行中，跳转 <span style="color:#3A84FF;cursor:pointer;">我的服务单</span> 查看进度</span>
      </template>
    </BkPopover>
    <BkCheckbox
      :disabled="isDestroied || isDestroing"
      :model-value="modelValue"
      style="margin-right:8px;vertical-align: middle;"
      @change="(value: boolean) => handleSelectChange(value, data)"
      @click="(e: Event) => e.stopPropagation()" />
    />
    <span :style="{color: isDestroied ? '#C4C6CC' : '#63656E'}">{{ data.cluster }}</span>
    <BkTag
      class="tag-tip"
      :style="{color: isDestroied ? '#63656E' : '#EA3536'}"
      :theme="isDestroied ? undefined : 'danger'">
      {{ data.status }}
    </BkTag>
  </div>
</template>
<script setup lang="ts">
  import  { type DataRow, DataRowStatus } from './Index.vue';

  interface Props {
    data: DataRow;
    modelValue: boolean;
  }

  interface Emits {
    (e: 'on-select-change', checked: boolean, data: DataRow): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isDestroied = computed(() => props.data.status === DataRowStatus.DESTROIED);
  const isDestroing = computed(() => props.data.status === DataRowStatus.DESTROING);

  const handleSelectChange = (checked: boolean, data: DataRow) => {
    emits('on-select-change', checked, data);
  };

</script>
<style lang="less" scoped>
.first-column {
  display: flex;
  align-items: center;

  .tag-tip {
    padding: 1px 4px;
    font-weight: 700;
    transform : scale(0.83,0.83);
  }
}
</style>
