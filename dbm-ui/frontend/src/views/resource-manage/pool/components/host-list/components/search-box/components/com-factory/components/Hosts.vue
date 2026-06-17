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
  <IpSearch
    :model-value="localValue"
    style="flex: 1"
    @clear="fetchData"
    @search="fetchData" />
</template>
<script setup lang="ts">
  import { batchSplitRegex } from '@common/regex';

  import IpSearch from '@views/resource-manage/common/components/ip-search/Index.vue';

  interface Props {
    defaultValue?: string;
  }

  type Emits = (e: 'change', value: Props['defaultValue']) => void;

  defineOptions({
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const localValue = ref('');

  watch(
    () => props.defaultValue,
    () => {
      if (props.defaultValue) {
        localValue.value = props.defaultValue.split(',').join('\n');
      } else {
        localValue.value = '';
      }
    },
    {
      immediate: true,
    },
  );

  const fetchData = (value: string) => {
    emits('change', value.split(batchSplitRegex).join(','));
  };
</script>
