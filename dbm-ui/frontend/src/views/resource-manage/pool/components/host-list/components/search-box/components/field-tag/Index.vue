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
  <div class="search-field-tag">
    <div class="header">
      <DbIcon
        style="margin-right: 8px; font-size: 13px; color: #979ba5"
        type="funnel" />
      <div>{{ t('搜索项：') }}</div>
    </div>
    <div class="tag-wrapper">
      <ValueTag
        v-for="tag in tags"
        :key="tag.name"
        ref="valueTagRef"
        :model="modelValue"
        :name="tag.name"
        :value="tag.value"
        @change="handleChange"
        @remove="handleRemove" />
    </div>
    <div v-if="Object.keys(modelValue).length < 1">--</div>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { isValueEmpty } from '../utils';

  import ValueTag from './ValueTag.vue';

  interface Props {
    modelValue: Record<string, any>;
  }

  interface Emits {
    (e: 'update:modelValue', value: Record<string, any>): void;
    (e: 'submit'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const valueTagRef = ref();

  // 地域/可用区/园区三个字段合并为一个 tag 展示与编辑
  const zoneFamilyFields = ['bk_cloud_region', 'bk_cloud_zone', 'subzone_ids'];

  const tags = computed(() => {
    const result: { name: string; value: any }[] = [];
    const zoneFamilyValue: Record<string, any> = {};
    Object.entries(props.modelValue).forEach(([name, value]) => {
      if (zoneFamilyFields.includes(name)) {
        if (!isValueEmpty(value)) {
          zoneFamilyValue[name] = value;
        }
        return;
      }
      if (isValueEmpty(value)) {
        return;
      }
      result.push({ name, value });
    });
    if (Object.keys(zoneFamilyValue).length > 0) {
      result.push({ name: 'city', value: zoneFamilyValue });
    }
    return result;
  });

  const handleChange = (fieldName: string, fieldValue: any) => {
    const result = { ...props.modelValue };

    if (fieldName === 'city') {
      // 聚合 tag 提交的是整组字段
      zoneFamilyFields.forEach((key) => {
        if (isValueEmpty(fieldValue[key])) {
          delete result[key];
        } else {
          result[key] = fieldValue[key];
        }
      });
    } else if (isValueEmpty(fieldValue)) {
      delete result[fieldName];
    } else {
      result[fieldName] = fieldValue;
    }

    emits('update:modelValue', result);
    emits('submit');
  };

  const handleRemove = (name: string) => {
    const result = { ...props.modelValue };
    if (name === 'city') {
      zoneFamilyFields.forEach((key) => delete result[key]);
    } else {
      delete result[name];
    }

    emits('update:modelValue', result);
    emits('submit');
  };
</script>
<style lang="less">
  .search-field-tag {
    display: flex;
    align-items: flex-start;
    padding: 0 20px;

    .header {
      display: flex;
      flex-shrink: 0;
      height: 22px;
      padding-right: 2px;
      color: #63656e;
      align-items: center;
    }

    .tag-wrapper {
      display: flex;
      flex-wrap: wrap;
    }
  }
</style>
