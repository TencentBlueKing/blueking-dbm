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
    v-test="{ type: 'column', value: 'resoureTag' }"
    field="labels"
    :label="t('资源标签')"
    :min-width="200"
    :rowspan="rowspan"
    :rules="rules">
    <template #head>
      <span class="mr-4">{{ t('资源标签') }}</span>
      <BatchEditColumn
        v-model="showBatchEdit"
        :all-option-id="DEFAULT_TAG_ID"
        :all-option-text="t('通用无标签')"
        display-key="value"
        filterable
        id-key="id"
        :list="tagList"
        :loading="loading"
        multiple
        multiple-mode="tag"
        :placeholder="t('请选择')"
        :popover-min-width="200"
        show-all
        :title="t('资源标签')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
        <template #tagRender="{ label, value }">
          {{ value === DEFAULT_TAG_ID ? t('通用无标签') : label }}
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
      </BatchEditColumn>
      <span class="custom-required" />
    </template>
    <EditableSelect
      v-model="ids"
      :all-option-id="DEFAULT_TAG_ID"
      :all-option-text="t('通用无标签')"
      display-key="value"
      filterable
      id-key="id"
      :list="tagList"
      :loading="loading"
      multiple
      multiple-mode="tag"
      :popover-min-width="200"
      show-all
      :tag-theme="tagTheme"
      @change="handleChange">
      <template #tagRender="{ label: tagLabel, value }">
        {{ value === DEFAULT_TAG_ID ? t('通用无标签') : tagLabel }}
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
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listTag } from '@services/source/tag';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  type IValue = ServiceReturnType<typeof listTag>['results'][0];

  interface Props {
    bizId?: number;
    rowspan?: number;
  }

  type Emits = (e: 'batch-edit', value: any, field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: window.PROJECT_CONFIG.BIZ_ID,
    rowspan: 1,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<
    {
      id: number;
      value: string;
    }[]
  >({
    required: true,
  });

  const { t } = useI18n();

  // 默认值为 0，表示通用无标签（指未包含任何标签的主机）
  const DEFAULT_TAG_ID = 0;
  const ids = ref<number[]>([]);
  const tagList = ref<IValue[]>([]);
  const tagMap = ref<Record<string, any>>({});
  const showBatchEdit = ref(false);
  const tagTheme = ref('');

  const rules = [
    {
      message: t('资源标签不能为空'),
      trigger: 'change',
      validator: () => {
        modelValue.value = ids.value.filter((id) => id !== DEFAULT_TAG_ID).map((item) => tagMap.value[item]);
        return Boolean(ids.value.length);
      },
    },
  ];

  const { loading, run: runListTag } = useRequest(listTag, {
    manual: true,
    onSuccess: (data) => {
      if (!data.results.length) {
        return;
      }
      tagList.value = data.results;
      tagMap.value = data.results.reduce<Record<string, any>>(
        (acc, item) => {
          Object.assign(acc, {
            [item.id]: item,
            [item.value]: item,
          });
          return acc;
        },
        {
          [DEFAULT_TAG_ID]: {
            id: DEFAULT_TAG_ID,
            type: 'resource',
            value: t('通用无标签'),
          },
          [t('通用无标签')]: {
            id: DEFAULT_TAG_ID,
            type: 'resource',
            value: t('通用无标签'),
          },
        },
      );
    },
  });

  watch(
    () => props.bizId,
    () => {
      runListTag({
        bk_biz_ids: String(props.bizId),
        type: 'resource',
      });
    },
    {
      immediate: true,
    },
  );

  const handleChange = (values: number[]) => {
    ids.value = values;
    tagTheme.value = values[0] === DEFAULT_TAG_ID ? 'success' : '';
  };

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (values: number[]) => {
    const labels = values.map((id) => tagMap.value[id]);
    emits('batch-edit', labels, 'labels');
  };

  const updateModel = (data: UnwrapRef<typeof modelValue>) => {
    const [firstItem] = data;
    if (firstItem?.id === DEFAULT_TAG_ID) {
      return;
    }
    const list = data.reduce<IValue[]>((acc, item: { id: number; value: string }) => {
      const tagInfo = Object.assign(item, tagMap.value[item?.value || item?.id]);
      if (tagInfo.id && tagInfo.value) {
        acc.push(tagInfo);
      }
      return acc;
    }, []);
    if (!list.length) {
      return;
    }
    ids.value = list.map((item) => item.id);
    tagTheme.value = ids.value[0] === DEFAULT_TAG_ID ? 'success' : '';
  };

  watch(modelValue, () => {
    updateModel(modelValue.value);
  });

  watch(
    tagList,
    () => {
      const [firstItem] = modelValue.value;
      if (!firstItem?.value) {
        // 如果没有传入值，则默认设置为通用无标签
        modelValue.value = [
          {
            id: DEFAULT_TAG_ID,
            value: t('通用无标签'),
          },
        ];
        ids.value = [DEFAULT_TAG_ID];
        tagTheme.value = 'success';
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .custom-required::after {
    margin-left: 4px;
    line-height: 20px;
    color: #ea3636;
    content: '*';
  }
</style>
