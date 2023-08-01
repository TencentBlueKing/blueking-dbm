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
  <BkDialog
    class="account-dialog"
    :draggable="false"
    :esc-close="false"
    height="auto"
    :is-show="props.isShow"
    :quick-close="false"
    :title="$t('新建账号')"
    :width="480"
    @closed="handleClose">
    <BkAlert
      class="mb-16"
      closable
      theme="warning"
      :title="$t('账号名创建后_不支持修改_密码创建后平台将不会显露_请谨记')" />
    <BkForm
      v-if="props.isShow"
      ref="accountRef"
      class="mb-36"
      form-type="vertical"
      :model="state.formData"
      :rules="rules">
      <BkFormItem
        :label="$t('账户名')"
        property="user"
        required>
        <BkInput
          v-model="state.formData.user"
          v-bk-tooltips="{
            trigger: 'click',
            placement: 'right',
            theme: 'light',
            content: userPlaceholder
          }"
          :placeholder="userPlaceholder" />
      </BkFormItem>
      <BkFormItem
        ref="passwordItemRef"
        :label="$t('密码')"
        property="password"
        required>
        <BkInput
          ref="passwordRef"
          v-model="state.formData.password"
          :placeholder="$t('请输入')"
          type="password"
          @blur="handlePasswordBlur"
          @focus="handlePasswordFocus" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
  <div
    id="passwordStrength"
    class="password-strength-wrapper">
    <div class="password-strength">
      <div
        v-for="(item, index) of passwordState.strength"
        :key="index"
        class="password-strength__item">
        <span
          class="password-strength__status"
          :class="[getStrenthStatus(item)]" />
        <span class="password-strength__content">{{ item.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import JSEncrypt from 'jsencrypt';
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { createAccount, getPasswordPolicy, getRSAPublicKeys, verifyPasswordStrength  } from '@services/permission';
  import type { PasswordStrengthVerifyInfo } from '@services/spider/permission';
  import type { PasswordPolicy, PasswordPolicyFollow, PasswordStrength } from '@services/types/permission';

  import { useGlobalBizs } from '@stores';

  import { dbTippy } from '@common/tippy';

  import {
    PASSWORD_POLICY,
    type PasswordPolicyKeys,
  } from '../common/consts';
  import type { StrengthItem } from '../common/types';

  const props = defineProps({
    isShow: {
      type: Boolean,
      default: false,
    },
  });

  const emits = defineEmits(['update:isShow', 'success']);

  const { t } = useI18n();
  const globalbizsStore = useGlobalBizs();

  const state = reactive({
    formData: {
      password: '',
      user: '',
    },
    isLoading: false,
    publicKey: '',
  });

  const verifyPassword = () => {
    verifyPasswordStrength(globalbizsStore.currentBizId, getEncyptPassword())
      .then((res) => {
        passwordState.validate = res;
        return res.is_strength;
      });
  };

  const userPlaceholder = t('Spider账号规则');
  const debounceVerifyPassword = _.debounce(verifyPassword, 300);
  const rules = {
    user: [{
      trigger: 'change',
      message: userPlaceholder,
      validator: (value: string) => /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,31}$/g.test(value),
    }],
    password: [{
      trigger: 'blur',
      message: t('密码不满足要求'),
      validator: debounceVerifyPassword,
    }],
  };

  watch(() => props.isShow, (show: boolean) => {
    if (show) {
      fetchRSAPublicKeys();
      fetchPasswordPolicy();
      passwordState.validate = {} as PasswordStrength;
      passwordState.strength = [];
    }
  });

  const fetchRSAPublicKeys = () =>  {
    getRSAPublicKeys({ names: ['mysql'] })
      .then((res) => {
        state.publicKey = res[0]?.content || '';
      });
  };

  const getEncyptPassword = () =>  {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(state.publicKey);
    const encyptPassword = encypt.encrypt(state.formData.password);
    return typeof encyptPassword === 'string' ? encyptPassword : '';
  };

  const passwordState = reactive({
    instance: null as Instance | null,
    isShow: false,
    strength: [] as StrengthItem[],
    keys: Object.keys(PASSWORD_POLICY).filter(key => !key.includes('follow_')),
    followKeys: Object.keys(PASSWORD_POLICY).filter(key => key.includes('follow_')),
    validate: {} as PasswordStrength,
  });
  const passwordRef = ref();
  const passwordItemRef = ref();

  watch(() => state.formData.password, (psw) => {
    psw && debounceVerifyPassword();
  });

  const fetchPasswordPolicy = () => {
    getPasswordPolicy('mysql')
      .then((res) => {
        const {
          min_length: minLength,
          max_length: maxLength,
          follow,
        } = res;

        passwordState.strength = [{
          keys: ['min_length_valid', 'max_length_valid'],
          text: t('密码长度为_min_max', [minLength, maxLength]),
        }];

        // 常规提示
        for (const key of passwordState.keys) {
          if (res[key as keyof PasswordPolicy]) {
            passwordState.strength.push({
              keys: [`${key}_valid`],
              text: t(PASSWORD_POLICY[key as PasswordPolicyKeys]),
            });
          }
        }

        // 重复提示
        if (follow.repeats) {
          passwordState.strength.push({
            keys: ['repeats_valid'],
            text: t('不能连续重复n位字母_数字_特殊符号', { n: follow.limit }),
          });
        }

        // 特殊提示（键盘序、字符序、数字序等）
        const special = passwordState.followKeys.reduce((values: StrengthItem[], key: string) => {
          const valueKey = key.replace('follow_', '') as keyof PasswordPolicyFollow;
          if (res.follow[valueKey]) {
            values.push({
              keys: [`${key}_valid`],
              text: t(PASSWORD_POLICY[key as PasswordPolicyKeys]),
            });
          }
          return values;
        }, []);

        if (special.length > 0) {
          const keys: string[] = [];
          const texts: string[] = [];
          for (const item of special) {
            keys.push(...item.keys);
            texts.push(item.text);
          }
          passwordState.strength.push({
            keys,
            text: texts.join('、'),
          });
        }

        // 设置 tips
        const template = document.getElementById('passwordStrength');
        const content = template?.querySelector?.('.password-strength');
        if (passwordRef.value?.$el && content) {
          const el = passwordRef.value.$el as HTMLDivElement;
          passwordState.instance?.destroy();
          passwordState.instance = dbTippy(el, {
            trigger: 'manual',
            theme: 'light',
            content,
            arrow: true,
            placement: 'right-start',
            interactive: true,
            allowHTML: true,
            hideOnClick: false,
            zIndex: 9999,
            onDestroy: () => template?.append?.(content),
            appendTo: () => document.body,
          });
        }
      });
  };

  const handlePasswordFocus = () => {
    passwordState.instance?.show();
    passwordItemRef.value?.clearValidate();
  };

  const handlePasswordBlur = () => {
    passwordState.instance?.hide();
  };

  const getStrenthStatus = (item: StrengthItem) => {
    if (!passwordState.validate || Object.keys(passwordState.validate).length === 0) {
      return '';
    }

    const isPass = item.keys.every((key) => {
      const verifyInfo = passwordState.validate.password_verify_info || {};
      return verifyInfo[key as keyof PasswordStrengthVerifyInfo];
    });
    return `password-strength__status--${isPass ? 'success' : 'failed'}`;
  };

  const accountRef = ref();
  const handleSubmit = async () => {
    await accountRef.value.validate();
    state.isLoading = true;
    if (!state.publicKey) {
      await fetchRSAPublicKeys();
    }

    const params = {
      ...state.formData,
      password: getEncyptPassword(),
    };
    createAccount(params, globalbizsStore.currentBizId)
      .then(() => {
        Message({
          message: t('账号创建成功'),
          theme: 'success',
          delay: 1500,
        });
        emits('success');
        handleClose();
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  const handleClose = () => {
    emits('update:isShow', false);
    state.formData.password = '';
    state.formData.user = '';
    passwordState.instance?.destroy();
    passwordState.instance = null;
    passwordState.validate = {} as PasswordStrength;
    passwordState.strength = [];
  };
</script>


<style lang="less" scoped>
  @import "@styles/mixins.less";

  .password-strength {
    padding-top: 4px;
    font-size: @font-size-mini;

    &__item {
      padding-bottom: 4px;
      .flex-center();
    }

    &__status {
      width: 6px;
      height: 6px;
      margin-right: 8px;
      background-color: @bg-disable;
      border-radius: 50%;

      &--success {
        background-color: @bg-success;
      }

      &--failed {
        background-color: @bg-danger;
      }
    }
  }
</style>
