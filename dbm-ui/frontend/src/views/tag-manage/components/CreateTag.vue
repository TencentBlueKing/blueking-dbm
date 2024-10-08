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
        property="tag">
        <BkTagInput
          ref="inputRef"
          v-model="formModel.tags"
          allow-auto-match
          allow-create
          has-delete-icon />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <div class="footer-wrapper">
        <BkButton
          class="mr-8"
          :disabled="formModel.tags.length === 0 || existedTagsSet.size > 0"
          :loading="createLoading || validateLoading"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          :loading="validateLoading"
          @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createTag, validateTag } from '@services/source/tag';
  import type { BizItem } from '@services/types';

  interface Props {
    biz: BizItem;
  }

  interface Emits {
    (e: 'create'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const formRef = useTemplateRef('formRef');
  const inputRef = useTemplateRef('inputRef');

  const existedTagsSet = ref<Set<string>>(new Set());

  const formModel = reactive({
    tags: [] as string[],
  });

  const rules = computed(() => {
    const existedArr = formModel.tags.filter((item) => existedTagsSet.value.has(item));
    return {
      tag: [
        {
          validator: () => existedArr.length === 0,
          message: t('n 已存在', { n: existedArr.join(',') }),
        },
      ],
    };
  });

  const { loading: validateLoading, run: runValidate } = useRequest(validateTag, {
    manual: true,
    onSuccess(data) {
      existedTagsSet.value = new Set(data.map((item) => item.value));
      nextTick(() => {
        formRef.value!.validate();
      });
    },
  });
  const { loading: createLoading, run: runCreate } = useRequest(createTag, {
    manual: true,
    onSuccess() {
      handleSubmit();
    },
  });

  watch(
    () => formModel.tags,
    (tags) => {
      runValidate({
        bk_biz_id: props.biz.bk_biz_id,
        tags: tags.map((tag) => ({ key: 'dbresource', value: tag })),
      });
    },
  );

  watch(isShow, () => {
    if (isShow.value) {
      nextTick(() => {
        inputRef.value?.focusInputTrigger();
        formModel.tags = [];
      });
    }
  });

  const handleConfirm = async () => {
    await formRef.value!.validate();
    runCreate({
      bk_biz_id: props.biz.bk_biz_id,
      tags: formModel.tags.map((tag) => ({ key: 'dbresource', value: tag })),
    });
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleSubmit = () => {
    isShow.value = false;
    emits('create');
  };
</script>

<style lang="less" scoped>
  .header-wrapper {
    display: flex;
    align-items: center;
    font-size: 14px;
    color: #979ba5;

    .title {
      font-size: 20px;
      color: #313238;
    }

    .title-divider {
      margin: 0 8px 0 11px;
    }
  }
</style>
