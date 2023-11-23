<!--
  TencentBlueKing is pleased to support the open source community by making
  蓝鲸智云 - 审计中心 (BlueKing - Audit Center) available.
  Copyright (C) 2023 THL A29 Limited,
  a Tencent company. All rights reserved.
  Licensed under the MIT License (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at http://opensource.org/licenses/MIT
  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on
  an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
  We undertake not to change the open source license (MIT license) applicable
  to the current version of the project delivered to anyone in the future.
-->
<template>
  <BkDialog
    class="permission-dialog"
    :close-icon="false"
    :is-show="isShow"
    width="768">
    <BkLoading :loading="loading">
      <div>no perimission</div>
    </BkLoading>
    <template #footer>
      <BkButton
        theme="primary"
        @click="handleGoApply">
        {{ t('去申请') }}
      </BkButton>
      <BkButton
        theme="primary"
        @click="handleApplyed">
        {{ t('已申请') }}
      </BkButton>
      <BkButton
        class="ml8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const isShow = ref(false);
  const loading  = ref(false);

  const handleGoApply = () => {
    console.log('handleGoApply');
  };

  const handleApplyed = () => {
    console.log('handleApplyed');
  };

  const handleCancel = () => {
    console.log('handleCancel');
  };
</script>
<style lang="less">
  .permission-dialog {
    .bk-modal-header {
      display: none;
    }
  }
</style>
