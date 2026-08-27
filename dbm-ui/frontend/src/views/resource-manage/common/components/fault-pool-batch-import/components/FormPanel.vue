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
  <div class="batch-import-form-panel">
    <div class="title">
      {{ t('批量导入资源池') }}
    </div>
    <BkForm
      ref="formRef"
      class="mt-16"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('所属业务')"
        property="for_biz"
        required>
        <DbSelect
          v-model="formData.for_biz"
          :allow-empty-values="[0]">
          <DbOption
            v-for="bizItem in bizList"
            :key="bizItem.bk_biz_id"
            :label="bizItem.display_name"
            :value="bizItem.bk_biz_id" />
        </DbSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('所属DB')"
        property="resource_type"
        required>
        <DbSelect v-model="formData.resource_type">
          <DbOptionGroup group-style="divider">
            <DbOption
              v-for="item in editResourceDbTypes"
              :key="item.value"
              :label="item.label"
              :value="item.value" />
          </DbOptionGroup>
          <DbOptionGroup group-style="divider">
            <DbOption
              :label="specialOptionLabelMap[SpecialOptions.PUBLIC]"
              :value="SpecialOptions.PUBLIC" />
          </DbOptionGroup>
        </DbSelect>
      </BkFormItem>
      <BkFormItem
        v-if="formData.for_biz !== 0"
        :label="t('资源标签')"
        property="labels">
        <TagSelector
          ref="tagSelectorRef"
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

  import { editResourceDbTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  interface Expose {
    getValue: () => Promise<{
      for_biz: number;
      label_names: string[];
      labels: number[];
      resource_type: string;
    }>;
  }

  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();

  const formRef = useTemplateRef('formRef');
  const tagSelectorRef = useTemplateRef('tagSelectorRef');

  const formData = reactive({
    for_biz: 0,
    labels: [] as number[],
    resource_type: '',
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
        bk_biz_id: 0,
        type: 'resource',
      },
    ],
    onSuccess(data) {
      tagList.value = data.results;
    },
  });

  defineExpose<Expose>({
    getValue() {
      return formRef.value!.validate().then(() => ({
        for_biz: Number(formData.for_biz),
        label_names: tagSelectorRef.value?.getLabelNames() || [],
        labels: formData.labels,
        resource_type: formData.resource_type,
      }));
    },
  });
</script>

<style lang="less">
  .batch-import-form-panel {
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
