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
      {{ t('批量添加资源归属') }}
    </div>
    <BkAlert
      class="mt-12"
      closable
      theme="warning">
      {{ t('为主机添加或更新所属 DB、标签设置，若设置不存在则添加，已存在则覆盖更新') }}
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
          disabled>
          <BkOption
            v-for="bizItem in bizList"
            :key="bizItem.bk_biz_id"
            :label="bizItem.display_name"
            :value="bizItem.bk_biz_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('所属DB')"
        property="resource_type"
        required>
        <BkSelect v-model="formData.resource_type">
          <BkOption
            v-for="item in dbTypeList"
            :key="item.id"
            :label="item.name"
            :value="item.id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('资源标签')"
        property="labels"
        required>
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

  import { getBizs } from '@services/source/cmdb';
  import { fetchDbTypeList } from '@services/source/infras';
  import { listTag } from '@services/source/tag';

  import TagSelector from '../../tag-selector/Index.vue';

  interface Props {
    bizId: number;
  }

  interface Expose {
    getValue: () => Promise<{
      labels: [];
      resource_type: string;
      for_biz: number;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const formRef = useTemplateRef('formRef');

  const formData = reactive({
    for_biz: 0,
    resource_type: '',
    labels: [],
  });

  const bizList = shallowRef<
    {
      bk_biz_id: number;
      display_name: string;
    }[]
  >([]);
  const dbTypeList = shallowRef<
    {
      id: string;
      name: string;
    }[]
  >([]);
  const tagList = shallowRef<
    {
      id: number;
      name: string;
    }[]
  >([]);

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        { bk_biz_id: 0, display_name: t('公共资源池') },
        ...data.map((item) => ({
          bk_biz_id: item.bk_biz_id,
          display_name: item.display_name,
        })),
      ];
    },
  });

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      const cloneData = data;
      cloneData.unshift({
        id: 'PUBLIC',
        name: t('通用'),
      });
      dbTypeList.value = cloneData;
    },
  });

  useRequest(listTag, {
    onSuccess(data) {
      tagList.value = data.results.map((item) => ({
        id: item.id,
        name: item.value,
      }));
    },
    defaultParams: [
      {
        bk_biz_id: props.bizId,
      },
    ],
  });

  watch(
    () => props.bizId,
    () => (formData.for_biz = props.bizId),
    {
      immediate: true,
    },
  );

  defineExpose<Expose>({
    getValue() {
      return formRef.value!.validate().then(() => ({
        for_biz: Number(formData.for_biz),
        resource_type: formData.resource_type,
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
