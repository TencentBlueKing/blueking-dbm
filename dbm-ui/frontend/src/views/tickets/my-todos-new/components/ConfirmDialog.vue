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
    v-model:is-show="isShow"
    :close-icon="false"
    draggable
    :quick-close="false"
    :title="title">
    <BkForm
      ref="firstFormRef"
      :form-type="tagConfig.data.length > 1 ? 'vertical' : 'horizontal'"
      :label-width="82"
      :model="formData">
      <BkFormItem
        :label="t('操作意见:')"
        :required="tagConfig.data.length > 1">
        <div v-if="tagConfig.data.length === 1">
          <div
            v-for="tag in tagConfig.data"
            :key="tag.name">
            <BkTag :theme="tag.theme">{{ tag.name }}</BkTag>
            <span
              v-if="tag.desc"
              class="ml-8">
              {{ tag.desc }}
            </span>
          </div>
        </div>
        <BkRadioGroup
          v-else
          v-model="formData.action"
          class="radio-box"
          :class="[{ 'radio-box__vertical': tagConfig.layout }]"
          @change="handleChange">
          <BkRadio
            v-for="tag in tagConfig.data"
            :key="tag.action"
            :label="tag.action">
            <BkTag :theme="tag.theme">{{ tag.name }}</BkTag>
            <span
              v-if="tag.desc"
              class="ml-8">
              {{ tag.desc }}
            </span>
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
    </BkForm>
    <BkForm
      ref="formRef"
      class="mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('备注')"
        property="content"
        :required="isRequired">
        <BkInput
          v-model="formData.content"
          :maxlength="100"
          :placeholder="t('请输入')"
          type="textarea" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script lang="ts">
  export type TagLayout = 'horizontal' | 'vertical';
  export interface TagItem {
    name: string;
    action: string;
    theme: BKTagTheme;
    desc?: string;
  }
  export interface IFormData {
    action: string;
    content: string;
  }
  export interface Props {
    isShow: boolean;
    title: string;
    tagConfig: {
      layout?: TagLayout;
      data: Array<TagItem>;
    };
  }
</script>
<script setup lang="ts">
  import type { Form } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'submit', value: IFormData): Promise<void>;
    (e: 'close'): void;
  }
  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    tagConfig: () => ({
      layout: 'horizontal',
      data: [] as Array<TagItem>,
    })
  });
  const emits = defineEmits<Emits>();
  const { t } = useI18n();
  const formData = reactive<IFormData>({
    action: '',
    content: '',
  });
  const firstFormRef = ref<InstanceType<typeof Form>>();
  const formRef = ref<InstanceType<typeof Form>>();
  const isRequired = ref(false);
  const isShow = computed(() => props.isShow);
  watch(
    () => props.isShow,
    (value) => {
      if (!value) {
        formRef.value!.clearValidate();
        formData.content = '';
        isRequired.value = false;
      }
    },
  );
  watch(
    () => props.tagConfig.data,
    (data) => {
      if (data.length) {
        const [first] = data;
        formData.action = first.action;
        if (first.theme === 'danger') {
          isRequired.value = true;
        }
      }
    },
  );
  const handleChange = (action: string) => {
    const [refuseItem] = props.tagConfig.data.filter((item) => item.theme === 'danger');
    isRequired.value = action === refuseItem.action;
  };
  const handleSubmit = () => {
    emits('submit', { ...formData });
  };
  const handleCancel = () => {
    emits('close');
  };
</script>

<style lang="less">
  .radio-box {
    display: flex;
    flex-wrap: wrap;

    .bk-radio {
      margin-right: 16px;
    }

    .bk-radio ~ .bk-radio {
      margin-left: 0;
    }
  }

  .radio-box__vertical {
    flex-direction: column;
  }
</style>
