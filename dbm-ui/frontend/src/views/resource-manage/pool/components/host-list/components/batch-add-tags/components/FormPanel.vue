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
  <div class="batch-assign-form-panel">
    <div class="title">
      {{ t('添加资源标签') }}
    </div>
    <BkAlert
      class="mt-12"
      closable
      theme="warning">
      {{ t('为主机添加资源标签，若标签不存在则添加，已存在则忽略') }}
    </BkAlert>
    <BkForm
      ref="formRef"
      class="mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('所属业务')"
        property="for_biz"
        required>
        <BkSelect
          v-model="formData.for_biz"
          :allow-empty-values="[0]"
          disabled>
          <BkOption
            v-for="bizItem in bizList"
            :key="bizItem.bk_biz_id"
            :label="bizItem.display_name"
            :value="bizItem.bk_biz_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('资源标签')"
        property="labels">
        <TagSelector
          v-model="formData.labels"
          :bk-biz-id="formData.for_biz" />
      </BkFormItem>
    </BkForm>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listTag } from '@services/source/tag';
  import type { BizItem } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  interface Props {
    bizId: number;
  }

  interface Expose {
    getValue: () => Promise<{
      labels: number[];
      for_biz: number;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const formRef = useTemplateRef('formRef');

  const formData = reactive({
    for_biz: 0,
    labels: [] as number[],
  });

  const tagList = shallowRef<ServiceReturnType<typeof listTag>['results']>([]);

  const bizList = computed(() => [
    {
      bk_biz_id: 0,
      display_name: t('公共资源池'),
    } as BizItem,
    ...globalBizsStore.bizs,
  ]);

  useRequest(listTag, {
    defaultParams: [
      {
        bk_biz_id: props.bizId,
      },
    ],
    onSuccess(data) {
      tagList.value = data.results;
    },
  });

  watch(
    () => props.bizId,
    () => {
      formData.for_biz = props.bizId;
    },
    {
      immediate: true,
    },
  );

  defineExpose<Expose>({
    getValue() {
      return formRef.value!.validate().then(() => ({
        for_biz: Number(formData.for_biz),
        labels: formData.labels,
      }));
    },
  });
</script>

<style lang="less">
  .batch-assign-form-panel {
    padding: 16px 24px;

    .title {
      font-size: 20px;
      line-height: 28px;
      color: #313238;
    }

    .search-input {
      margin: 14px 0 12px;
    }
  }
</style>
