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
  <div class="render-cluster-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="$t('请输入或选择集群')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@views/redis/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue?: IDataRow['cluster']
  }

  interface Emits {
    (e: 'change', value: string): void
    (e: 'onInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }


  const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const localValue = ref(props.modelValue);
  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标集群不能为空'),
    },
  ];

  const handleInputFinish = (value: string) => {
    emits('onInputFinish', value);
  };

  watch(() => localValue.value, () => {
    emits('change', localValue.value);
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-box {
    position: relative;
  }
</style>
