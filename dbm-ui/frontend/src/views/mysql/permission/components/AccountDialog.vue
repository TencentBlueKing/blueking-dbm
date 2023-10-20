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
    :is-show="isShow"
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
      v-if="isShow"
      ref="accountRef"
      class="mb-36"
      form-type="vertical"
      :model="state.formdata"
      :rules="rules">
      <BkFormItem
        :label="$t('账户名')"
        property="user"
        required>
        <BkInput
          v-model="state.formdata.user"
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
          v-model="state.formdata.password"
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
<script lang="ts">
  import { Message } from 'bkui-vue';
  import JSEncrypt from 'jsencrypt';
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import {
    createAccount,
    getPasswordPolicy,
    getRSAPublicKeys,
    verifyPasswordStrength,
  } from '@services/permission';

  import { useGlobalBizs } from '@stores';

  import { dbTippy } from '@common/tippy';

  import {
    PASSWORD_POLICY,
    type PasswordPolicyKeys,
  } from '../common/const';

  interface StrengthItem {
    keys: string[],
    text: string
  }

  type PasswordPolicy = ServiceReturnType<typeof getPasswordPolicy>;
  type IncludeRule = PasswordPolicy
  type ExcludeContinuousRule = PasswordPolicy['follow']
  type PasswordStrength = ServiceReturnType<typeof verifyPasswordStrength>;
  type PasswordStrengthVerifyInfo = PasswordStrength['password_verify_info']

  export default {
    name: 'PermissionAccount',
  };
</script>

<script setup lang="ts">
  interface Emits {
    (e: 'success'): void
  }

  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const globalbizsStore = useGlobalBizs();

  const state = reactive({
    formdata: {
      password: '',
      user: '',
    },
    isLoading: false,
    publicKey: '',
  });
  const userPlaceholder = t('由字母_数字_下划线_点_减号_字符组成以字母或数字开头');
  const debounceVerifyPassword = _.debounce(verifyPassword, 300);
  const rules = {
    user: [{
      trigger: 'change',
      message: userPlaceholder,
      validator: (value: string) => /^[a-z0-9][a-z0-9-_.]*$/g.test(value),
    }],
    password: [{
      trigger: 'blur',
      message: t('密码不满足要求'),
      validator: debounceVerifyPassword,
    }],
  };

  watch(isShow, (show: boolean) => {
    if (show) {
      fetchRSAPublicKeys();
      fetchPasswordPolicy();
      passwordState.validate = {} as PasswordStrength;
      passwordState.strength = [];
    }
  });

  /**
   * 获取公钥
   */
  function fetchRSAPublicKeys() {
    getRSAPublicKeys({ names: ['mysql'] })
      .then((res) => {
        state.publicKey = res[0]?.content || '';
      });
  }

  /**
   * 获取加密密码
   */
  function getEncyptPassword() {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(state.publicKey);
    const encyptPassword = encypt.encrypt(state.formdata.password);
    return typeof encyptPassword === 'string' ? encyptPassword : '';
  }

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

  /** 校验密码 */
  watch(() => state.formdata.password, (psw) => {
    psw && debounceVerifyPassword();
  });

  /**
   * 远程校验密码是否符合要求
   */
  function verifyPassword() {
    return verifyPasswordStrength(globalbizsStore.currentBizId, getEncyptPassword())
      .then((res) => {
        passwordState.validate = res;
        return res.is_strength;
      });
  }

  /**
   * 获取密码安全策略
   */
  function fetchPasswordPolicy() {
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
          if (res[key as keyof IncludeRule]) {
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
          const valueKey = key.replace('follow_', '') as keyof ExcludeContinuousRule;
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
  }

  /**
   * 密码框获取焦点
   */
  function handlePasswordFocus() {
    passwordState.instance?.show();
    // 清除校验信息
    passwordItemRef.value?.clearValidate();
  }

  /**
   * 密码框失去焦点
   */
  function handlePasswordBlur() {
    passwordState.instance?.hide();
  }

  /**
   * 获取密码当前项是否校验
   */
  function getStrenthStatus(item: StrengthItem) {
    if (!passwordState.validate || Object.keys(passwordState.validate).length === 0) {
      return '';
    }

    const isPass = item.keys.every((key) => {
      const verifyInfo = passwordState.validate.password_verify_info || {};
      return verifyInfo[key as keyof PasswordStrengthVerifyInfo];
    });
    return `password-strength__status--${isPass ? 'success' : 'failed'}`;
  }

  /**
   * 提交表单数据
   */
  const accountRef = ref();
  async function handleSubmit() {
    await accountRef.value.validate();
    state.isLoading = true;
    if (!state.publicKey) {
      await fetchRSAPublicKeys();
    }

    const params = {
      ...state.formdata,
      password: getEncyptPassword(),
    };
    createAccount(params, globalbizsStore.currentBizId)
      .then((res) => {
        Message({
          message: t('账号创建成功'),
          theme: 'success',
        });
        emits('success');
        handleClose();
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  /**
   * 关闭 dialog
   */
  function handleClose() {
    isShow.value = false;
    state.formdata.password = '';
    state.formdata.user = '';
    passwordState.instance?.destroy();
    passwordState.instance = null;
    passwordState.validate = {} as PasswordStrength;
    passwordState.strength = [];
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .account-dialog {
    .bk-button {
      width: 64px;
    }
  }

  .password-strength-wrapper {
    position: relative;
    z-index: -1;
    display: none;
  }

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
