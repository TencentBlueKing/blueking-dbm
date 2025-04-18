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
    <DisasterToleranceLevelItem
      v-model="modelValue.disaster_tolerance_level"
      :type="type" />
    <CityCodeItem v-model="modelValue" />
    <SubzonesItem
      v-if="showSubZoneItem"
      v-model="modelValue.sub_zone_ids"
      :city-code="modelValue.city_code"
      :disaster-tolerance-level="modelValue.disaster_tolerance_level" />
  </DbCard>
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { Affinity } from '@common/const';

  import CityCodeItem from './components/CityCode.vue';
  import DisasterToleranceLevelItem from './components/DisasterToleranceLevel.vue';
  import SubzonesItem from './components/Subzones.vue';

  interface Props {
    type?: ComponentProps<typeof DisasterToleranceLevelItem>['type'];
  }

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

  defineProps<Props>();

  const modelValue = defineModel<{
    city_code: string;
    city_name?: string;
    disaster_tolerance_level: string;
    sub_zone_ids: number[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSubZoneItem = computed(
    () =>
      modelValue.value.disaster_tolerance_level &&
      modelValue.value.city_code &&
      ([Affinity.CROS_SUBZONE, Affinity.SAME_SUBZONE_CROSS_SWTICH].includes(
        modelValue.value.disaster_tolerance_level as Affinity,
      ) ||
        (modelValue.value.disaster_tolerance_level === Affinity.NONE && modelValue.value.city_code !== 'default')),
  );

  defineExpose<Expose>({
    getValue() {
      const { city_code: city, disaster_tolerance_level: affinity, sub_zone_ids: subZoneIds } = modelValue.value;
      // 跨园区-指定多个园区 / 指定园区 / 无容灾要求且指定地域
      if (
        (affinity === Affinity.CROS_SUBZONE && subZoneIds.length > 0) ||
        affinity === Affinity.SAME_SUBZONE_CROSS_SWTICH ||
        (affinity === Affinity.NONE && subZoneIds.length > 0)
      ) {
        return {
          affinity,
          location_spec: {
            city,
            include_or_exclue: true,
            sub_zone_ids: subZoneIds,
          },
        };
      }

      // 跨园区-随机可用区 / 不限园区 / 无容灾要求且地域无限制
      return {
        affinity,
        location_spec: {
          city,
        },
      };
    },
  });
</script>
