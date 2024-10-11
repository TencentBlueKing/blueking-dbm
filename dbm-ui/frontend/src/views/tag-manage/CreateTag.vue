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
  <BkDialog
    :is-show="isShow"
    render-directive="if"
    :title="computedTitle"
    @closed="handleClose"
    @confirm="handleConfirm">
    <BkForm
      ref="formRef"
      form-type="vertical"
      :model="formModel"
      :rules="rules">
      <BkFormItem
        :label="t('标签')"
        required>
        <BkTagInput
          v-model="formModel.tags"
          allow-create
          :clearable="false"
          has-delete-icon />
      </BkFormItem>
    </BkForm>
  </BkDialog>
</template>

<script setup lang="tsx">
  import type { Form } from 'bkui-vue';
  import { computed, reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { createResourceTag, getAllResourceTags } from '@services/source/resourceTag';

  import type { BizItem } from '@/services/types';

  export type ValidateInfo = {
    res: boolean;
    message: string;
  };

  interface Props {
    isShow: boolean;
    biz: BizItem;
  }

  interface Emit {
    (e: 'update:isShow', value: boolean): void;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<Emit>();

  const { t } = useI18n();
  const existedTagsSet = ref<Set<string>>(new Set());
  const formRef = useTemplateRef<InstanceType<typeof Form>>('formRef');
  const submitLoading = ref(false);
  const formModel = reactive({
    tags: [],
  });

  const computedTitle = computed(() => `${t('新建标签')} - ${props.biz.name}`);

  const rules = computed(() => {
    const { res, message } = handleValidate(formModel.tags);
    return [
      {
        validator: () => res,
        message,
      },
    ];
  });

  watch(
    () => formModel.tags,
    async () => {
      const { results } = await getAllResourceTags();
      existedTagsSet.value = new Set(results);
      await formRef.value?.validate();
    },
  );

  const handleValidate = (arrVal: string[]) => {
    const validateInfo: ValidateInfo = {
      res: true,
      message: '',
    };

    if (!arrVal.length) {
      return { ...validateInfo, res: false, message: '' };
    }

    const existedArr = arrVal.filter((item) => existedTagsSet.value.has(item));
    const validateRes = existedArr.length === 0;

    return {
      ...validateInfo,
      res: validateRes,
      message: validateRes ? '' : t('n 已存在', { n: existedArr.join(',') }),
    };
  };

  const handleConfirm = async () => {
    submitLoading.value = true;
    try {
      await createResourceTag({
        tags: formModel.tags,
      });
      handleClose();
    } finally {
      submitLoading.value = false;
    }
  };

  const handleClose = () => {
    emit('update:isShow', false);
  };
</script>
