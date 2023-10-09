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
  <BkLoading :loading="isLoading">
    <DbForm
      class="password-policy"
      :label-width="260">
      <DbCard :title="t('密码组成')">
        <BkFormItem
          :label="t('密码长度')"
          required>
          <BkInput
            v-model="formData.min_length"
            class="password-policy-number"
            :max="formData.max_length"
            :min="8"
            type="number" />
          <span class="password-policy-text">{{ t('至') }}</span>
          <BkInput
            v-model="formData.max_length"
            class="password-policy-number"
            :max="32"
            :min="formData.min_length"
            type="number" />
          <span class="password-policy-text">{{ t('最小长度_8_最大长度_32') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('密码必须包含')"
          required>
          <BkCheckbox
            v-model="formData.lowercase"
            :false-label="false">
            {{ t('小写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.uppercase"
            :false-label="false">
            {{ t('大写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.numbers"
            :false-label="false">
            {{ t('数字') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.symbols"
            :false-label="false">
            {{ t('特殊字符_除空格外') }}
          </BkCheckbox>
        </BkFormItem>
        <BkFormItem :label="t('密码不允许连续N位出现')">
          <p class="mb-8">
            <span
              class="password-policy-text mr-8"
              style="padding: 0;">N = </span>
            <BkInput
              v-model="formData.follow.limit"
              class="password-policy-number"
              :min="3"
              type="number" />
          </p>
          <BkCheckbox
            v-model="formData.follow.keyboards"
            :false-label="false">
            {{ t('键盘序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.follow.letters"
            :false-label="false">
            {{ t('字母序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.follow.numbers"
            :false-label="false">
            {{ t('数字序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.follow.symbols"
            :false-label="false">
            {{ t('连续特殊符号序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.follow.repeats"
            :false-label="false">
            {{ t('重复字母_数字_特殊符号') }}
          </BkCheckbox>
        </BkFormItem>
      </DbCard>
      <BkFormItem class="password-policy-footer">
        <BkButton
          class="mr-8"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit()">
          {{ t('保存') }}
        </BkButton>
        <BkButton
          :disabled="isSubmitting"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
      </BkFormItem>
    </DbForm>
  </BkLoading>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import {
    getPasswordPolicy,
    updatePasswordPolicy,
  } from '@services/permission';

  import { useInfo } from '@hooks';

  const initData = () => ({
    follow: {
      keyboards: false,
      letters: false,
      limit: 3,
      numbers: false,
      repeats: false,
      symbols: false,
    },
    lowercase: true,
    max_length: 32,
    min_length: 8,
    numbers: true,
    symbols: true,
    uppercase: true,
  });

  const { t } = useI18n();
  const accountType = 'mysql';

  // const passwordPolicyData = {
  //   id: 0,
  //   name: '',
  // };

  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const formData = reactive(initData());

  const fetchPasswordPolicy = () => {
    isLoading.value = true;
    getPasswordPolicy(accountType)
      .then((passwordPolicy) => {
        Object.assign(formData, passwordPolicy);
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  fetchPasswordPolicy();

  const handleReset = () => {
    useInfo({
      title: t('确认重置'),
      content: t('重置将会恢复默认设置的内容'),
      onConfirm: () => {
        Object.assign(formData, initData());
        handleSubmit(t('重置成功'));
        return true;
      },
    });
  };

  const handleSubmit = (message = t('保存成功')) => {
    isSubmitting.value = true;
    updatePasswordPolicy({
      account_type: accountType,
      policy: formData,
    })
      .then(() => {
        Message({
          theme: 'success',
          message,
        });
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>

<style lang="less" scoped>
  .password-policy {
    font-size: @font-size-mini;

    .password-policy-number {
      width: 68px;
    }

    .password-policy-text {
      display: inline-block;
      padding: 0 8px;
    }

    .bk-checkbox {
      display: flex;
      width: max-content;
      padding: 8px 0;
      margin-left: 0;
    }

    .password-policy-footer {
      margin: 32px 0 0 24px;

      .bk-button {
        width: 88px;
      }
    }
  }
</style>
