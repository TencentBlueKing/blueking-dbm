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
    v-model="modelValue"
    :allow-empty-values="[0]"
    filterable
    :loading="isLoading"
    :placeholder="t('请选择地域')">
    <BkOption
      v-for="item in cityList"
      :key="item.bk_idc_city_id"
      :label="item.bk_idc_city_name"
      :value="item.bk_idc_city_id">
    </BkOption>
  </BkSelect>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listLogicCities } from '@services/source/infras';

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

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const { data: cityList, loading: isLoading } = useRequest(listLogicCities);

  defineExpose<Expose>({
    getValue() {
      if (!_.isNumber(modelValue.value)) {
        return;
      }
      return {
        city_meta: {
          city: (cityList.value || []).find((item) => item.bk_idc_city_id === Number(modelValue.value))!
            .bk_idc_city_name,
          city_id: String(modelValue.value),
        },
      };
    },
  });
</script>
