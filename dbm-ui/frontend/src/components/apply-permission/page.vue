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
  <div class="dbm-perimission-page">
    <div class="perimission-page-container">
      <RenderResult :data="data" />
      <div class="perimission-page-footer">
        <BkButton
          v-if="!isApplyed"
          :disabled="data.hasPermission"
          theme="primary"
          @click="handleGoApply">
          {{ t('去申请') }}
        </BkButton>
        <BkButton
          v-else
          theme="primary"
          @click="handleApplyed">
          {{ t('已申请') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    Button as BkButton,
  } from 'bkui-vue';
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type ApplyDataModel from '@services/model/iam/apply-data';

  import RenderResult from './render-result.vue';

  interface Props {
    data: ApplyDataModel
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const isApplyed = ref(false);

  const handleGoApply = () => {
    isApplyed.value = true;
    window.open(props.data.apply_url, '_blank');
  };

  const handleApplyed = () => {
    window.location.reload();
  };

</script>
<style lang="less" scoped>
  .dbm-perimission-page {
    display: flex;
    align-items: center;
    height: 100%;

    .perimission-page-container {
      width: 768px;
      padding: 24px;
      margin: 60px auto;
      background-color: #fff;
      border-radius: 2px;
      box-shadow: 0 1px 2px 0 rgb(0 0 0 / 5%);
    }

    .perimission-page-footer {
      margin: 24px auto 6px;
      text-align: center;
    }
  }
</style>
