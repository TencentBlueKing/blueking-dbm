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
    :loading="isLoading"
    :model-value="defaultValue"
    multiple
    :placeholder="t('请选择机型')"
    :remote-method="remoteMethod"
    :scroll-height="384"
    @change="handleChange"
    @scroll-end="handleScrollEnd">
    <BkOption
      v-for="(item, index) in deviceList"
      :key="`${item}#${index}`"
      :label="item"
      :value="item">
      {{ item }}
    </BkOption>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  interface Props {
    defaultValue?: string;
  }

  interface Emits {
    (e: 'change', value: string): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const deviceList = ref<string[]>([]);
  const scrollLoading = ref(false);

  const searchParams = {
    offset: 0,
    limit: 12,
    name: '',
  };

  let isAppend = false;

  const { loading: isLoading, run: getDeviceClassList } = useRequest(fetchDeviceClass, {
    defaultParams: [searchParams],
    onSuccess(data) {
      const deviceClassList = data.results.map((item) => item.device_type);
      if (isAppend) {
        deviceList.value.push(...deviceClassList);
        return;
      }

      deviceList.value = deviceClassList;
    },
  });

  const handleScrollEnd = () => {
    scrollLoading.value = true;
    isAppend = true;
    searchParams.offset += searchParams.limit;
    getDeviceClassList(searchParams);
  };

  const remoteMethod = (value: string) => {
    isAppend = false;
    searchParams.name = value;
    searchParams.offset = 0;
    getDeviceClassList(searchParams);
  };

  const handleChange = (value: string[]) => {
    emits('change', value.join(','));
  };
</script>
