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
    :is-loading="createLoading || validateLoading"
    :is-show="isShow"
    render-directive="if"
    @closed="handleClose"
    @confirm="handleConfirm">
    <template #header>
      <div class="header-wrapper">
        <span class="title">{{ t('新建标签') }}</span>
        <span class="title-divider">|</span>
        <span class="biz-name">
          {{ biz?.name }}
        </span>
      </div>
    </template>
    <BkForm
      ref="formRef"
      form-type="vertical"
      :model="formModel"
      :rules="rules">
      <BkFormItem
        :label="t('标签')"
        required>
        <BkTagInput
          ref="inputRef"
          v-model="formModel.tags"
          allow-auto-match
          allow-create
          has-delete-icon />
      </BkFormItem>
    </BkForm>
  </BkDialog>
</template>

<script setup lang="tsx">
  import type { Form } from 'bkui-vue';
  import { computed, reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createTag, validateTag } from '@services/source/tag';
  import type { BizItem } from '@services/types';

  interface Props {
    isShow: boolean;
    biz: BizItem | undefined;
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<Emits>();

  const { t } = useI18n();
  const existedTagsSet = ref<Set<string>>(new Set());
  const formRef = useTemplateRef<InstanceType<typeof Form>>('formRef');
  const inputRef = useTemplateRef<HTMLInputElement>('inputRef');
  const { loading: validateLoading, run: runValidate } = useRequest(validateTag, {
    manual: true,
    onSuccess(data) {
      const { duplicated_values } = data;
      existedTagsSet.value = new Set(duplicated_values);
      formRef.value?.validate();
    },
  });
  const { loading: createLoading, run: runCreate } = useRequest(createTag, {
    manual: true,
    onSuccess() {
      handleClose();
    },
  });

  const formModel = reactive<{
    tags: string[];
  }>({
    tags: [],
  });

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
    async (tags) => {
      runValidate({
        bk_biz_id: props.biz?.bk_biz_id as number,
        values: tags,
      });
    },
  );

  const handleValidate = (arrVal: string[]) => {
    const validateInfo = {
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
    runCreate({
      bk_biz_id: props.biz?.bk_biz_id as number,
      type: 'system',
      key: 'resource',
      value: formModel.tags,
    });
  };

  const handleClose = () => {
    emit('update:isShow', false);
  };

  onMounted(() => {
    inputRef.value?.focus();
  });
</script>

<style lang="less" scoped>
  .header-wrapper {
    display: flex;
    align-items: center;
    color: #979ba5;
    font-size: 14px;

    .title {
      font-size: 20px;
      color: #313238;
    }

    .title-divider {
      margin: 0 8px 0 11px;
    }
  }
</style>
