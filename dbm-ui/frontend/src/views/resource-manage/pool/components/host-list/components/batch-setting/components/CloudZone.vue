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
    v-model="modelValue"
    filterable
    :loading="isLoading"
    :placeholder="t('请选择云可用区')">
    <DbOption
      v-for="item in zoneList"
      :key="item"
      :label="getCloudZoneName(item) || item"
      :value="item" />
  </DbSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCloudZones } from '@services/source/infras';

  import { getCloudZoneName } from '@common/const';

  interface Props {
    formData: {
      bk_cloud_region: string;
      city_meta: string;
    };
  }

  interface Expose {
    getValue: () => { bk_cloud_zone: string } | undefined;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  // 层级限制：云可用区候选按已选 云区域 + 城市 过滤（city_meta 存城市代码，与接口 city_code 同域）
  const {
    data: zoneData,
    loading: isLoading,
    run,
  } = useRequest(getInfrasCloudZones, {
    manual: true,
  });

  watch(
    () => [props.formData.bk_cloud_region, props.formData.city_meta],
    ([region, cityCode]) => {
      modelValue.value = '';
      run({
        city_code: cityCode || undefined,
        region: region || undefined,
      });
    },
    { immediate: true },
  );

  const zoneList = computed(() => (zoneData.value || []).map((item) => item.bk_cloud_zone));

  defineExpose<Expose>({
    getValue() {
      if (!modelValue.value) {
        return;
      }
      return {
        bk_cloud_zone: modelValue.value,
      };
    },
  });
</script>
