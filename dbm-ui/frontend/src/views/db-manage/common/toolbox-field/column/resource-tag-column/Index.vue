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
  <EditableColumn
    :label="t('资源标签')"
    :min-width="150">
    <EditableSelect
      v-model="modelValue"
      :all-option-id="-1"
      :all-option-text="t('非专用资源')"
      collapse-tags
      display-key="value"
      filterable
      id-key="id"
      :list="tagList"
      multiple
      multiple-mode="tag"
      show-all
      :tag-theme="tagTheme"
      @change="handleChange">
      <template #tagRender="{ label, value }">
        {{ value === -1 ? t('非专用资源') : label }}
      </template>
      <template #allOptionIcon>
        <BkTag
          class="mr-4"
          size="small"
          theme="info"
          type="filled">
          {{ t('享') }}
        </BkTag>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listTag } from '@services/source/tag';

  type IValue = ServiceReturnType<typeof listTag>['results'][0];

  const modelValue = defineModel<number[]>({
    required: true,
  });

  const selected = defineModel<IValue[]>('selected', {
    default: () => [] as IValue[],
    required: true,
  });

  const { t } = useI18n();

  const tagList = ref<IValue[]>([]);
  const tagMap = ref<Record<number, any>>({});

  const tagTheme = computed(() => (modelValue.value.length === 1 && modelValue.value[0] === -1 ? 'success' : ''));

  useRequest(listTag, {
    defaultParams: [
      {
        type: 'resource',
      },
    ],
    onSuccess: (data) => {
      tagList.value = data.results;
      tagMap.value = data.results.reduce<Record<number, any>>(
        (acc, item) => {
          Object.assign(acc, {
            [item.id]: item,
          });
          return acc;
        },
        {
          [-1]: {
            id: -1,
            type: 'resource',
            value: t('非专用资源'),
          },
        },
      );
      if (modelValue.value.length) {
        selected.value = modelValue.value.map((id) => tagMap.value[id]);
      }
    },
  });

  const handleChange = (value: number[]) => {
    selected.value = value.map((id) => tagMap.value[id]);
  };
</script>
