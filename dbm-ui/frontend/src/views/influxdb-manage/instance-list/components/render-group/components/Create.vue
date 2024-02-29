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
  <BkForm
    ref="formRef"
    class="group-form"
    :model="{ name }">
    <BkFormItem
      error-display-type="tooltips"
      property="name"
      required
      :rules="rules">
      <BkInput
        ref="inputRef"
        v-model="name"
        :placeholder="t('以小写英文字母开头_且只能包含英文字母_数字_连字符')"
        @blur="handleClose"
        @click.stop
        @enter="handleSubmit" />
    </BkFormItem>
  </BkForm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { nameRegx } from '@common/regex';

  import { messageError } from '@utils';

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

  const { t } = useI18n();

  const formRef = ref();
  const inputRef = ref();
  const name = ref(props.originName);
  const rules = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'change',
    },
  ];

  onMounted(() => {
    inputRef.value?.focus?.();
  });

  const handleSubmit = () => {
    formRef.value
      ?.validate()
      .then(() => {
        if (name.value && props.originName !== name.value) {
          emits('change', name.value);
        }
        emits('close');
      })
      .catch((errorMessage: string) => {
        messageError(errorMessage);
      });
  };

  const handleClose = () => {
    emits('close');
  };
</script>

<style lang="less" scoped>
  .group-form {
    width: 100%;

    :deep(.bk-form-content) {
      margin: 0 !important;
    }
  }
</style>
