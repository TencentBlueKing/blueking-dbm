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
  <BkInput
    ref="inputRef"
    v-model="name"
    @blur="handleClose"
    @click.stop
    @enter="handleSubmit" />
</template>

<script setup lang="ts">
  interface Emits {
    (e: 'change', value: string): void;
    (e: 'close'): void;
  }

  interface Props {
    originName: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    originName: '',
  });
  const emits = defineEmits<Emits>();

  const inputRef = ref();
  const name = ref(props.originName);

  const handleSubmit = () => {
    if (name.value && props.originName !== name.value) {
      emits('change', name.value);
    }
    emits('close');
  };

  const handleClose = () => {
    emits('close');
  };

  onMounted(() => {
    inputRef.value?.focus?.();
  });
</script>

<style lang="less" scoped>
  .group-form {
    width: 100%;

    :deep(.bk-form-content) {
      margin: 0 !important;
    }
  }
</style>
