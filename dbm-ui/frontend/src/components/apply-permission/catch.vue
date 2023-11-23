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
  <div
    v-if="needApplyPermission"
    class="dbm-perimission-section">
    <div class="perimission-section-container">
      <RenderResult :data="permissionResult" />
      <div class="perimission-section-footer">
        <BkButton
          v-if="!isApplyed"
          :disabled="permissionResult.hasPermission"
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
  <slot v-else />
</template>
<script setup lang="ts">
  import {
    Button as BkButton,
  } from 'bkui-vue';
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ApplyDataModel from '@services/model/iam/apply-data';

  import { useEventBus } from '@hooks';

  import RenderResult from './render-result.vue';


  const isApplyed = ref(false);

  const { on } = useEventBus();
  const { t } = useI18n();

  const permissionResult = ref(new ApplyDataModel());
  const needApplyPermission = ref(false);

  const handleGoApply = () => {
    isApplyed.value = true;
    window.open(permissionResult.value.apply_url, '_blank');
  };

  const handleApplyed = () => {
    window.location.reload();
  };

  on('permission-catch', (data) => {
    needApplyPermission.value = true;
    permissionResult.value = data as ApplyDataModel;
  });

</script>
<style lang="less" scoped>
  .dbm-perimission-section {
    display: flex;
    align-items: center;
    height: 100%;

    .perimission-section-container {
      width: 768px;
      padding: 24px;
      margin: 60px auto;
      background-color: #fff;
      border-radius: 2px;
      box-shadow: 0 1px 2px 0 rgb(0 0 0 / 5%);
    }

    .perimission-section-footer {
      margin: 24px auto 6px;
      text-align: center;
    }
  }
</style>
