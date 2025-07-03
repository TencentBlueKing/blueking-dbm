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
    :min-width="200">
    <EditableSelect
      v-model="modelValue"
      :all-option-id="DEFAULT_TAG_ID"
      :all-option-text="t('非专用资源')"
      collapse-tags
      display-key="value"
      filterable
      id-key="id"
      :list="tagList"
      multiple
      multiple-mode="tag"
      :popover-min-width="200"
      show-all
      :tag-theme="tagTheme"
      @change="handleChange">
      <template #tagRender="{ label, value }">
        {{ value === DEFAULT_TAG_ID ? t('非专用资源') : label }}
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
  import _ from 'lodash';
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
  const tagInfoById = ref<Record<number, any>>({});
  const tagInfoByValue = ref<Record<string, any>>({});
  // 默认值为 0，表示非专用资源（指未包含任何标签的主机）
  const DEFAULT_TAG_ID = 0;

  const tagTheme = computed(() =>
    modelValue.value.length === 1 && modelValue.value[0] === DEFAULT_TAG_ID ? 'success' : '',
  );

  useRequest(listTag, {
    defaultParams: [
      {
        bk_biz_ids: [window.PROJECT_CONFIG.BIZ_ID, 0].join(','), // 0 表示公共资源池
        type: 'resource',
      },
    ],
    onSuccess: (data) => {
      if (!data.results.length) {
        return;
      }
      tagList.value = data.results;
      tagInfoById.value = data.results.reduce<Record<number, any>>(
        (acc, item) => {
          Object.assign(acc, {
            [item.id]: item,
          });
          return acc;
        },
        {
          [DEFAULT_TAG_ID]: {
            id: DEFAULT_TAG_ID,
            type: 'resource',
            value: t('非专用资源'),
          },
        },
      );
      tagInfoByValue.value = data.results.reduce<Record<string, any>>(
        (acc, item) => {
          Object.assign(acc, {
            [item.value]: item,
          });
          return acc;
        },
        {
          [t('非专用资源')]: {
            id: DEFAULT_TAG_ID,
            type: 'resource',
            value: t('非专用资源'),
          },
        },
      );
    },
  });

  const handleChange = (value: number[]) => {
    selected.value = value.map((id) => tagInfoById.value[id]);
  };

  const updateModelAndSelected = (data: any[]) => {
    const list = data.reduce<IValue[]>((acc, item: string | number) => {
      if (typeof item === 'string' && Boolean(tagInfoByValue.value[item]?.id)) {
        acc.push(tagInfoByValue.value[item]);
      }
      if (typeof item === 'number' && Boolean(tagInfoById.value[item]?.id)) {
        acc.push(tagInfoById.value[item]);
      }
      return acc;
    }, []);
    if (!list.length) {
      return;
    }
    modelValue.value = list.map((item) => item.id);
    selected.value = modelValue.value.map((id) => tagInfoById.value[id]);
  };

  watch(
    () => modelValue.value,
    (newValue, oldValue) => {
      if (!_.isEqual(newValue, oldValue)) {
        setTimeout(() => updateModelAndSelected(newValue), 200);
      }
    },
    { deep: true, immediate: true },
  );
</script>
