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
      class="k8s-city-code-item"
      :label="t('地域')"
      property="details.city_code"
      required>
      <BkRadioGroup
        v-model="modelValue"
        class="region-group">
        <div class="region-group-item-box">
          <div
            v-for="info of cityData"
            :key="info.regionCode"
            class="region-group-item">
            <BkRadioButton :label="info.regionCode">
              {{ info.regionName }}
            </BkRadioButton>
          </div>
        </div>
      </BkRadioGroup>
      <span class="region-tips">{{ t('如果对请求延时有要求_请尽量选择靠近接入点的地域') }}</span>
    </BkFormItem>
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRegions } from '@services/source/kubernetesToolbox';

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const { data: cityData, loading } = useRequest(getRegions);
</script>

<style lang="less">
  .k8s-city-code-item {
    .bk-form-content {
      min-height: 90px;
    }

    .region-group {
      width: 100% !important;

      .bk-radio-button-label {
        min-width: 100px;
        border-radius: 0;
      }

      .region-group-item-box {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
      }

      .region-group-item {
        position: relative;
        margin-bottom: 4px;
        margin-left: -1px;
      }
    }

    .region-group-flex-direction {
      flex-direction: column;
    }

    .region-tips {
      font-size: @font-size-mini;
      line-height: normal;
      color: @gray-color;
    }
  }
</style>
