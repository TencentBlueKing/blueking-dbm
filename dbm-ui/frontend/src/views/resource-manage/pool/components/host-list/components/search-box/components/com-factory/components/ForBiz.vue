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
  <DbAppSelect
    clearable
    :list="globalBizsStore.bizs"
    :model-value="currentApp"
    @change="handleChange">
  </DbAppSelect>
</template>
<script setup lang="ts">
  import { getBizs } from '@services/source/cmdb';

  import { useGlobalBizs } from '@stores';

  import DbAppSelect from '@components/db-app-select/Index.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    defaultValue?: string;
  }
  type Emits = (e: 'change', value: Props['defaultValue']) => void;

  interface Expose {
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    defaultValue: '',
  });

  const emits = defineEmits<Emits>();

  const globalBizsStore = useGlobalBizs();

  const currentApp = shallowRef<IAppItem>();

  watch(
    () => props.defaultValue,
    () => {
      if (props.defaultValue) {
        currentApp.value = globalBizsStore.bizIdMap.get(Number(props.defaultValue));
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (appInfo?: IAppItem) => {
    currentApp.value = appInfo;
    emits('change', appInfo ? String(appInfo.bk_biz_id) : '');
  };

  defineExpose<Expose>({
    reset() {
      currentApp.value = undefined;
      emits('change', undefined);
    },
  });
</script>
