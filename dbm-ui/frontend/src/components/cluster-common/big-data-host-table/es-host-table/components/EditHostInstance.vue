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
  <div
    ref="rootRef"
    class="es-cluster-node-edit-host-instance"
    @mouseenter="handleShowInput"
    @mouseleave="handleHideInput">
    <BkInput
      v-if="isShowInput"
      v-model="localValue"
      :min="1"
      type="number" />
    <span v-else>
      {{ localValue }}
    </span>
  </div>
</template>
<script setup lang="ts">
  import {
    nextTick,
    ref,
  } from 'vue';

  interface Props {
    modelValue: number
  }
  interface Emits {
    (e: 'change', value: number): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const rootRef = ref();
  const isShowInput = ref(false);

  const localValue = ref(props.modelValue);

  const handleShowInput = () => {
    isShowInput.value = true;
    nextTick(() => {
      rootRef.value.querySelector('input').focus();
    });
  };

  const handleHideInput = () => {
    isShowInput.value = false;
    if (localValue.value === props.modelValue) {
      return;
    }
    emits('change', localValue.value);
  };
</script>
<style lang="less">
  .es-cluster-node-edit-host-instance{
    display: block;
  }
</style>
