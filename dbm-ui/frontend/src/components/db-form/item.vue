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
  <BkFormItem
    ref="formItemRef"
    v-bind="attrs">
    <slot />
    <template
      v-if="$slots.label"
      #label>
      <slot name="label" />
    </template>
  </BkFormItem>
</template>
<script setup lang="ts">
  import {
    provide,
    ref,
    useAttrs,
  } from 'vue';


  const attrs = useAttrs();
  const formItemRef = ref();

  const clearValidate = () => {
    formItemRef.value.clearValidate();
  };

  const validate = () => formItemRef.value.validate();

  provide('DBMFormItem', {
    clearValidate,
    validate,
  });

  defineExpose({
    clearValidate,
    validate,
  });
</script>
