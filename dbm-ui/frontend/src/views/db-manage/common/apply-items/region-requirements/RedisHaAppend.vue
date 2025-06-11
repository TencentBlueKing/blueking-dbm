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
  <DbCard :title="t('地域要求')">
    <CityCodeItem v-model="modelValue" />
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import CityCodeItem from './components/CityCode.vue';

  interface Expose {
    getValue: () => {
      affinity: string;
      location_spec: {
        city: string;
        include_or_exclue?: boolean;
        sub_zone_ids?: number[];
      };
    };
  }

  const modelValue = defineModel<{
    city_code: string;
    city_name?: string;
    disaster_tolerance_level: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  defineExpose<Expose>({
    getValue() {
      const { city_code: city, disaster_tolerance_level: affinity } = modelValue.value;
      return {
        affinity,
        location_spec: {
          city,
        },
      };
    },
  });
</script>
