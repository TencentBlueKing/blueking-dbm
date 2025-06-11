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
  <BkLoading :loading="loading">
    <BkFormItem
      class="city_code_item"
      :label="t('地域')"
      property="details.city_code"
      required>
      <BkRadioGroup
        v-model="modelValue.city_code"
        class="region-group">
        <div
          v-for="info of radioList"
          :key="info.city_code"
          class="region-group-item">
          <BkRadioButton :label="info.city_code">
            {{ info.city_name }}
          </BkRadioButton>
        </div>
      </BkRadioGroup>
      <span class="region-tips">{{ t('如果对请求延时有要求_请尽量选择靠近接入点的地域') }}</span>
    </BkFormItem>
  </BkLoading>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasCities } from '@services/source/infras';

  import { Affinity } from '@common/const';

  const modelValue = defineModel<{
    city_code: string;
    city_name?: string;
    disaster_tolerance_level: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const radioList = shallowRef<UnwrapRef<typeof cityList>>();

  const { data: cityList, loading } = useRequest(getInfrasCities);

  watch([cityList, () => modelValue.value.disaster_tolerance_level], () => {
    if (cityList.value) {
      const showCityDefault = [Affinity.CROSS_RACK, Affinity.MAX_EACH_ZONE_EQUAL, Affinity.NONE].includes(
        modelValue.value.disaster_tolerance_level as Affinity,
      );
      if (showCityDefault) {
        radioList.value = cityList.value;
      } else {
        radioList.value = cityList.value.filter((cityItem) => cityItem.city_code !== 'default');
        if (modelValue.value.city_code === 'default') {
          modelValue.value.city_code = '';
        }
      }
    }
  });

  watch(
    () => modelValue.value.city_code,
    () => {
      modelValue.value.city_name = (cityList.value || []).find(
        (cityItem) => cityItem.city_code === modelValue.value.city_code,
      )?.city_name;
    },
  );
</script>

<style lang="less" scoped>
  .city_code_item {
    :deep(.bk-form-content) {
      min-height: 90px;
    }

    .region-group {
      display: flex;
      align-items: center;

      :deep(.bk-radio-button-label) {
        min-width: 100px;
        border-radius: 0;
      }

      .region-group-item {
        position: relative;
        margin-left: -1px;
      }
    }

    .region-tips {
      font-size: @font-size-mini;
      line-height: normal;
      color: @gray-color;
    }
  }
</style>
