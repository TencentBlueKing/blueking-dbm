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
  <DbCard :title="t('容灾要求')">
    <DisasterToleranceLevelItem
      v-model="modelValue.disaster_tolerance_level"
      type="bigdata" />
    <CloudItem
      v-model="modelValue.bk_cloud_id"
      @change="handleCloudChange" />
    <CityCodeItem v-model="modelValue" />
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import CloudItem from '@views/db-manage/common/apply-items/CloudItem.vue';

  import CityCodeItem from './components/CityCode.vue';
  import DisasterToleranceLevelItem from './components/DisasterToleranceLevel.vue';

  type Emits = (e: 'cloud-change', value: { id: number | string; name: string }) => void;

  interface Expose {
    getValue: () => {
      affinity: string;
      location_spec: {
        /** 地域标识；随机时 default */
        bk_cloud_region: string;
      };
    };
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    /** 地域标识，随机为 default */
    bk_cloud_region: string;
    disaster_tolerance_level: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const handleCloudChange = (value: { id: number | string; name: string }) => {
    emits('cloud-change', value);
  };

  defineExpose<Expose>({
    getValue() {
      const { bk_cloud_region: region, disaster_tolerance_level: affinity } = modelValue.value;
      // 大数据级别（尽量分散 / 跨机架 / 无）只填到地域，不选可用区
      return {
        affinity,
        location_spec: {
          bk_cloud_region: region || 'default',
        },
      };
    },
  });
</script>
