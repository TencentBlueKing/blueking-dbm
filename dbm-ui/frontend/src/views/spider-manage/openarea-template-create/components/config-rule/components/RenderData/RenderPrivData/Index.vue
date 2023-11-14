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
  <div class="priv-data-box">
    <BkButton
      :disabled="!clusterId"
      text
      theme="primary"
      @click="handleShowRule">
      <span v-if="modelValue.length < 1">
        <DbIcon type="add" />
        {{ t('添加授权规则') }}
      </span>
      <I18nT
        v-else
        keypath="已添加n个规则"
        tag="span">
        {{ modelValue.length }}
      </I18nT>
    </BkButton>
    <div
      v-if="errorMessage"
      class="error-flag">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
  </div>
  <PermissionRule
    v-model="modelValue"
    v-model:is-show="isShow"
    :cluster-id="clusterId" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import PermissionRule from './components/PermissionRule.vue';

  interface Props {
    clusterId: number,
  }

  interface Exposes {
    getValue: () => Promise<{
      priv_data: Array<number>
    }>
  }

  defineProps<Props>();

  const { t } = useI18n();

  const modelValue = defineModel<number[]>({
    default: [],
  });

  const isShow = ref(false);
  const errorMessage = ref('');

  const handleShowRule = () => {
    isShow.value = true;
  };

  defineExpose<Exposes>({
    getValue() {
      if (modelValue.value.length < 1) {
        errorMessage.value = t('初始化授权不能为空');
        return Promise.reject();
      }

      errorMessage.value = '';
      return Promise.resolve({
        priv_data: modelValue.value,
      });
    },
  });
</script>
<style lang="less" scoped>
  .priv-data-box{
    position: relative;
    padding: 0 16px;

    .error-flag {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 99;
      display: flex;
      padding-right: 6px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }
</style>

