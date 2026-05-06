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
  <BkSelect
    filterable
    :input-search="false"
    :loading="loading"
    :model-value="defaultValue"
    :placeholder="t('请选择操作系统类型')"
    @change="handleChange">
    <BkOptionGroup group-style="divider">
      <BkOption
        v-for="item in data"
        :key="item"
        :label="item"
        :value="item" />
    </BkOptionGroup>
    <BkOptionGroup group-style="divider">
      <BkOption
        :label="specialOptionLabelMap[SpecialOptions.EMPTY]"
        :value="SpecialOptions.EMPTY" />
    </BkOptionGroup>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getOsTypeList } from '@services/source/dbresourceResource';

  import { specialOptionLabelMap, SpecialOptions } from '@common/const';

  interface Props {
    defaultValue?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  defineOptions({
    inheritAttrs: false,
  });

  withDefaults(defineProps<Props>(), {
    defaultValue: () => '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { data, loading } = useRequest(getOsTypeList, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
      },
    ],
    initialData: [],
  });

  const handleChange = (value: string) => {
    emits('change', value);
  };
</script>
