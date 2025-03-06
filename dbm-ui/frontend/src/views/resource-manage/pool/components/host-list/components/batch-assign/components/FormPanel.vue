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
      {{ t('重新设置资源归属') }}
    </div>
    <BkAlert
      class="mt-12"
      closable
      theme="warning">
      {{
        isBusiness
          ? t('清空主机现有的所属 DB 和标签，重新进行设置')
          : t('清空主机现有的所属业务、所属 DB 、标签，重新进行设置')
      }}
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
          :disabled="isBusiness">
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
        property="labels">
        <TagSelector
          v-model="formData.labels"
          :bk-biz-id="formData.for_biz"
          :default-list="currentData?.labels" />
      </BkFormItem>
    </BkForm>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { getBizs } from '@services/source/cmdb';
  import { fetchDbTypeList } from '@services/source/infras';
  import { listTag } from '@services/source/tag';
  import type { BizItem } from '@services/types';

  import TagSelector from '@views/resource-manage/pool/components/tag-selector/Index.vue';

  interface Props {
    bizId: number;
    currentData?: {
      labels: DbResourceModel['labels'];
      resourceType: string;
    };
  }

  interface Expose {
    getValue: () => Promise<{
      for_biz: number;
      labels: number[];
      resource_type: string;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const formRef = useTemplateRef('formRef');

  const isBusiness = route.name === 'BizResourcePool';

  const formData = reactive({
    for_biz: isBusiness ? window.PROJECT_CONFIG.BIZ_ID : 0,
    labels: (props.currentData?.labels || []).map((labelItem) => labelItem.id),
    resource_type: props.currentData?.resourceType || '',
  });

  const bizList = shallowRef<ServiceReturnType<typeof getBizs>>([]);
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);
  const tagList = shallowRef<ServiceReturnType<typeof listTag>['results']>([]);

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        {
          bk_biz_id: 0,
          display_name: t('公共资源池'),
        } as BizItem,
        ...data,
      ];
    },
  });

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      dbTypeList.value = [
        {
          id: 'PUBLIC',
          name: t('通用'),
        },
        ...data,
      ];
    },
  });

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

  defineExpose<Expose>({
    getValue() {
      return formRef.value!.validate().then(() => ({
        for_biz: Number(formData.for_biz),
        labels: formData.labels,
        resource_type: formData.resource_type,
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
