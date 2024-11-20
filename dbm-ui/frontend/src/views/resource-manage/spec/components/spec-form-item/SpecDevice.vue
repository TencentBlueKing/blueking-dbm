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
  <div class="spec-mem spec-form-item">
    <div class="spec-form-item-label">
      {{ t('机型') }}
    </div>
    <div class="spec-form-item-content">
      <BkFormItem
        property="device_class"
        required
        :rules="rules"
        style="width: 100%">
        <BkSelect
          :allow-empty-values="['']"
          :clearable="false"
          filterable
          :input-search="false"
          :loading="isLoading"
          :model-value="modelValue"
          multiple
          :remote-method="remoteMethod"
          :scroll-height="384"
          :scroll-loading="scrollLoading"
          @change="handleSelectChange"
          @scroll-end="handleScrollEnd">
          <BkOption
            v-for="item in deviceClassList"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
      </BkFormItem>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  const { t } = useI18n();

  const modelValue = defineModel<string[] | string>({
    default: () => [],
  });

  const deviceClassList = ref<
    {
      label: string;
      value: string;
    }[]
  >([]);
  const scrollLoading = ref(false);

  const searchParams = {
    offset: 0,
    limit: 12,
    device_type: '',
  };

  const rules = [
    {
      required: true,
      validator: (value: string[]) => value.length > 0,
      message: t('请选择xx', [t('机型')]),
    },
  ];

  let isAppend = false;

  const { loading: isLoading, run: getDeviceClassList } = useRequest(fetchDeviceClass, {
    defaultParams: [searchParams],
    onSuccess(data) {
      scrollLoading.value = false;
      const deviceList = data.results.map((item) => ({
        label: `${item.device_type}(${item.cpu}${t('核')}${item.mem}G})`,
        value: item.device_type,
      }));
      if (isAppend) {
        deviceClassList.value.push(...deviceList);
        return;
      }

      deviceClassList.value = deviceList;
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
    searchParams.device_type = value;
    searchParams.offset = 0;
    getDeviceClassList(searchParams);
  };

  const handleSelectChange = (list: string[]) => {
    modelValue.value = list;
  };
</script>

<style lang="less" scoped>
  @import './specFormItem.less';
</style>
