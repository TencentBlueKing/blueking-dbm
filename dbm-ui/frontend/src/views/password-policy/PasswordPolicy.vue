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
  <BkLoading :loading="state.isLoading">
    <DbForm
      class="password-policy"
      :label-width="260">
      <DbCard :title="$t('密码组成')">
        <BkFormItem
          class="password-policy__length"
          :label="$t('密码长度')"
          required>
          <BkInput
            v-model="state.formdata.min_length"
            class="password-policy__number"
            :max="state.formdata.max_length"
            :min="8"
            type="number" />
          <span class="password-policy__text">{{ $t('至') }}</span>
          <BkInput
            v-model="state.formdata.max_length"
            class="password-policy__number"
            :max="32"
            :min="state.formdata.min_length"
            type="number" />
          <span class="password-policy__text">{{ $t('最小长度_8_最大长度_32') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="$t('密码必须包含')"
          required>
          <BkCheckbox
            v-model="state.formdata.lowercase"
            :false-label="false">
            {{ $t('小写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.uppercase"
            :false-label="false">
            {{ $t('大写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.numbers"
            :false-label="false">
            {{ $t('数字') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.symbols"
            :false-label="false">
            {{ $t('特殊字符_除空格外') }}
          </BkCheckbox>
        </BkFormItem>
        <BkFormItem :label="$t('密码不允许连续N位出现')">
          <p class="mb-8">
            <span
              class="password-policy__text mr-8"
              style="padding: 0;">N = </span>
            <BkInput
              v-model="state.formdata.follow.limit"
              class="password-policy__number"
              :min="3"
              type="number" />
          </p>
          <BkCheckbox
            v-model="state.formdata.follow.keyboards"
            :false-label="false">
            {{ $t('键盘序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.follow.letters"
            :false-label="false">
            {{ $t('字母序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.follow.numbers"
            :false-label="false">
            {{ $t('数字序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.follow.symbols"
            :false-label="false">
            {{ $t('连续特殊符号序') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="state.formdata.follow.repeats"
            :false-label="false">
            {{ $t('重复字母_数字_特殊符号') }}
          </BkCheckbox>
        </BkFormItem>
      </DbCard>
      <BkFormItem class="password-policy__footer">
        <BkButton
          class="mr-8"
          :loading="state.isSubmitting"
          theme="primary"
          @click="handleSubmit()">
          {{ $t('保存') }}
        </BkButton>
        <BkButton
          :disabled="state.isSubmitting"
          @click="handleReset">
          {{ $t('重置') }}
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

  import { AccountTypes } from '@/common/const';

  interface AccountTypeMap {
    [prop: string]: AccountTypes;
  }

  const { t } = useI18n();
  const router = useRouter();

  const state = reactive({
    isLoading: false,
    isSubmitting: false,
    formdata: initData(),
  });

  let accountType: AccountTypes;
  const accountTypeMap: AccountTypeMap = {
    PlatformPasswordPolicy: AccountTypes.MYSQL,
    PlatformSpiderPasswordPolicy: AccountTypes.TENDBCLUSTER,
  };

  // 在复用的页面之间进行路由跳转时，不会重新创建页面组件实例，故监听name变化改变accountType并重查数据
  watch(() => router.currentRoute.value.name, (newVal) => {
    accountType = accountTypeMap[newVal as string];

    // 防止路由切换到其他页面时，进行数据查询
    if (Object.values(accountTypeMap).includes(accountType)) {
      fetchPasswordPolicy();
    }
  }, {
    immediate: true,
  });

  // 重置数据
  function initData() {
    return {
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
    };
  }

  function fetchPasswordPolicy() {
    state.isLoading = true;
    getPasswordPolicy(accountType)
      .then((res) => {
        Object.assign(state.formdata, res);
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleReset() {
    useInfo({
      title: t('确认重置'),
      content: t('重置将会恢复默认设置的内容'),
      onConfirm: () => {
        Object.assign(state.formdata, initData());
        handleSubmit(t('重置成功'));
        return true;
      },
    });
  }

  function handleSubmit(message = t('保存成功')) {
    state.isSubmitting = true;
    updatePasswordPolicy({
      account_type: accountType,
      policy: state.formdata,
    })
      .then(() => {
        Message({
          theme: 'success',
          message,
        });
      })
      .finally(() => {
        state.isSubmitting = false;
      });
  }
</script>

<style lang="less" scoped>
  .password-policy {
    font-size: @font-size-mini;

    .password-policy__number {
      width: 68px;
    }

    .password-policy__text {
      display: inline-block;
      padding: 0 8px;
    }

    .bk-checkbox {
      display: flex;
      width: max-content;
      padding: 8px 0;
      margin-left: 0;
    }

    .password-policy__footer {
      margin: 32px 0 0 24px;

      .bk-button {
        width: 88px;
      }
    }
  }
</style>
