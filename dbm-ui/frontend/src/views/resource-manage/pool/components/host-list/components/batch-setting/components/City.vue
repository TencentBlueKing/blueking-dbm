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
    :placeholder="t('请选择城市')">
    <DbOption
      v-for="item in cityList"
      :key="item.city_code"
      :label="item.city_name"
      :value="item.city_code" />
  </DbSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities, getInfrasSubzonesByCity } from '@services/source/infras';

  interface Props {
    formData: {
      bk_cloud_region: string;
    };
  }

  interface Expose {
    getValue: () =>
      | {
          city_meta: {
            city: string;
            city_id: string;
          };
        }
      | undefined;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const { data: cityData, loading: isLoading } = useRequest(getInfrasCities);

  // 层级限制：城市候选按已选云区域过滤（该云区域下园区登记过的城市代码集合）
  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity);

  const cityList = computed(() => {
    const list = cityData.value || [];
    if (!props.formData.bk_cloud_region) {
      return list.filter((item) => item.city_name !== 'default');
    }
    const regionCityCodes = new Set(
      (subzoneList.value || [])
        .filter((item) => item.bk_cloud_region === props.formData.bk_cloud_region)
        .map((item) => item.bk_city_code),
    );
    return list.filter((item) => regionCityCodes.has(item.city_code));
  });

  watch(
    () => props.formData.bk_cloud_region,
    () => {
      modelValue.value = '';
    },
  );

  defineExpose<Expose>({
    getValue() {
      if (!modelValue.value) {
        return;
      }
      const matched = (cityList.value || []).find((item) => item.city_code === modelValue.value)!;
      return {
        city_meta: {
          city: matched.city_name,
          // cities 接口无独立城市 id，city_id 用城市代码
          city_id: matched.city_code,
        },
      };
    },
  });
</script>
