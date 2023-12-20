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
  <div class="render-switch-box">
    <TableEditSelect
      ref="selectRef"
      v-model="localValue"
      :list="selectList"
      :placeholder="t('请选择')"
      :rules="rules"
      @change="(value) => handleChange(value as string)" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  interface Props {
    data: string;
  }


  interface Exposes {
    getValue: () => Promise<string>
  }

  interface Emits {
    (e: 'type-change', value: string): void
  }

  const props = defineProps<Props>();


  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const selectRef = ref();
  const localValue = ref('KAFKA');

  const selectList = [
    {
      value: 'KAFKA',
      label: 'KAFKA',
    },
    {
      value: 'L5_AGENT',
      label: 'L5_AGENT',
    },
    {
      value: 'TCP/IP',
      label: 'TCP/IP',
    },
  ];

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择接收端类型'),
    },
  ];

  watch(() => props.data, (type) => {
    localValue.value = type;
  }, {
    immediate: true,
  });

  const handleChange = (value: string) => {
    localValue.value = value;
    emits('type-change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>
<style lang="less" scoped>
  .render-switch-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }
  }
</style>
