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
  <DbSelect
    filterable
    :input-search="false"
    :loading="isLoading"
    :model-value="modelValue"
    multiple
    multiple-mode="tag"
    :placeholder="t('请选择机型')"
    :scroll-height="384"
    @change="handleChange">
    <DbOptionGroup group-style="divider">
      <DbOption
        v-for="(item, index) in deviceList"
        :key="`${item}#${index}`"
        :label="item"
        :value="item">
        {{ item }}
      </DbOption>
    </DbOptionGroup>
    <DbOptionGroup group-style="divider">
      <DbOption
        :label="specialOptionLabelMap[SpecialOptions.EMPTY]"
        :value="SpecialOptions.EMPTY" />
    </DbOptionGroup>
  </DbSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchResourceHostDeviceClass } from '@services/source/dbresourceResource';

  import { specialOptionLabelMap, SpecialOptions } from '@common/const';

  interface Props {
    defaultValue?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  defineOptions({
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const modelValue = ref<string[]>([]);

  const { data: deviceList, loading: isLoading } = useRequest(fetchResourceHostDeviceClass, {
    initialData: [],
  });

  watch(
    () => props.defaultValue,
    () => {
      modelValue.value = (props.defaultValue || '').split(',');
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    emits('change', value.filter((item) => item).join(','));
  };
</script>
