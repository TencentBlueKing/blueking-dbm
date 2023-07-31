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
  <BkLoading :loading="isLoading">
    <BkInput
      ref="passwordRef"
      v-model="localValue"
      class="pass-input"
      :placeholder="$t('请输入连接密码')"
      :rules="rules"
      type="password"
      @blur="handlePasswordBlur"
      @focus="handlePasswordFocus" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue?: IDataRow['password'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
  });

  const { t } = useI18n();
  const localValue = ref(props.modelValue);

  const rules = [
    {
      validator: (value: string) => value !== '',
      message: t('密码不能为空'),
    },
  ];

  const handlePasswordBlur = () => {
    console.log('handlePasswordBlur: ', localValue.value);
  };

  const handlePasswordFocus = () => {
    console.log('handlePasswordFocus: ', localValue.value);
  };

  defineExpose<Exposes>({
    getValue: () => Promise.resolve(localValue.value),
  });

</script>
<style lang="less" scoped>
.pass-input {
  height: 40px;
  border: none;
  :deep(input) {
    padding-left: 16px !important;
  }
}
</style>
