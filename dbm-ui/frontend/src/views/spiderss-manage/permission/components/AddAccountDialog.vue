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
    :title="t('新建账号')"
    :width="480"
    @closed="handleClose">
    <BkAlert
      class="mb-16"
      closable
      theme="warning"
      :title="t('账号名创建后_不支持修改_密码创建后平台将不会显露_请谨记')" />
    <BkForm
      v-if="isShow"
      ref="accountRef"
      class="mb-36"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <BkFormItem
        :label="t('账户名')"
        property="user"
        required>
        <BkInput
          v-model="formData.user"
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
        :label="t('密码')"
        property="password"
        required>
        <BkInput
          ref="passwordRef"
          v-model="formData.password"
          :placeholder="t('请输入')"
          type="password"
          @blur="handlePasswordBlur"
          @focus="handlePasswordFocus" />
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
  <div
    id="passwordStrength"
    class="password-strength-wrapper">
    <div class="password-strength">
      <div
        v-for="(item, index) of strength"
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
  import { useRequest } from 'vue-request';

  import { createAccount, getPasswordPolicy, getRSAPublicKeys, verifyPasswordStrength } from '@services/permission';
  import type { PasswordPolicy, PasswordPolicyFollow, PasswordStrength, PasswordStrengthVerifyInfo  } from '@services/types/permission';

  import { AccountTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import {
    PASSWORD_POLICY,
    type PasswordPolicyKeys,
  } from '../common/consts';
  import type { StrengthItem } from '../common/types';

  import { useGlobalBizs } from '@/stores';

  interface Emits {
    (e: 'success'): void,
  }

  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const { MYSQL, TENDBCLUSTER } = AccountTypes;
  let instance: Instance | null = null;
  let publicKey = '';

  const keys: string[] = [];
  const followKeys: string[] = [];

  Object.keys(PASSWORD_POLICY).forEach((key) => {
    if (key.includes('follow_')) followKeys.push(key);
    else keys.push(key);
  });

  const formData = reactive({
    password: '',
    user: '',
  });
  const isLoading = ref(false);
  const strength = ref<StrengthItem[]>([]);
  const validate = ref<PasswordStrength>({} as PasswordStrength);
  const passwordRef = ref();
  const passwordItemRef = ref();

  const verifyPassword = () => verifyPasswordStrength(currentBizId, getEncyptPassword(), TENDBCLUSTER)
    .then((res) => {
      validate.value = res;
      return res.is_strength;
    });

  const userPlaceholder = t('Spider账号规则');
  const debounceVerifyPassword = _.debounce(verifyPassword, 300);
  const rules = {
    user: [
      {
        trigger: 'change',
        message: userPlaceholder,
        validator: (value: string) => /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,31}$/g.test(value),
      },
    ],
    password: [
      {
        trigger: 'blur',
        message: t('密码不满足要求'),
        validator: debounceVerifyPassword,
      },
    ],
  };

  watch(isShow, (show: boolean) => {
    if (show) {
      fetchRSAPublicKeys();
      fetchPasswordPolicy(TENDBCLUSTER);
      validate.value = {} as PasswordStrength;
      strength.value = [];
    }
  });

  const fetchRSAPublicKeys = () =>  {
    getRSAPublicKeys({ names: [MYSQL] })
      .then((res) => {
        publicKey = res[0]?.content || '';
      });
  };

  const getEncyptPassword = () =>  {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(publicKey);
    const encyptPassword = encypt.encrypt(formData.password);
    return typeof encyptPassword === 'string' ? encyptPassword : '';
  };

  watch(() => formData.password, (psw) => {
    psw && debounceVerifyPassword();
  });

  const { run: fetchPasswordPolicy } = useRequest(getPasswordPolicy, {
    manual: true,
    onSuccess(res) {
      const {
        min_length: minLength,
        max_length: maxLength,
        follow,
      } = res;

      strength.value = [{
        keys: ['min_length_valid', 'max_length_valid'],
        text: t('密码长度为_min_max', [minLength, maxLength]),
      }];

      // 常规提示
      for (const key of keys) {
        if (res[key as keyof PasswordPolicy]) {
          strength.value.push({
            keys: [`${key}_valid`],
            text: t(PASSWORD_POLICY[key as PasswordPolicyKeys]),
          });
        }
      }

      // 重复提示
      if (follow.repeats) {
        strength.value.push({
          keys: ['repeats_valid'],
          text: t('不能连续重复n位字母_数字_特殊符号', { n: follow.limit }),
        });
      }

      // 特殊提示（键盘序、字符序、数字序等）
      const special = followKeys.reduce((values, key: string) => {
        const valueKey = key.replace('follow_', '') as keyof PasswordPolicyFollow;
        if (res.follow[valueKey]) {
          values.push({
            keys: [`${key}_valid`],
            text: t(PASSWORD_POLICY[key as PasswordPolicyKeys]),
          });
        }
        return values;
      }, [] as StrengthItem[]);

      if (special.length > 0) {
        const keys: string[] = [];
        const texts: string[] = [];
        for (const item of special) {
          keys.push(...item.keys);
          texts.push(item.text);
        }
        strength.value.push({
          keys,
          text: texts.join('、'),
        });
      }

      // 设置 tips
      const template = document.getElementById('passwordStrength');
      const content = template?.querySelector?.('.password-strength');
      if (passwordRef.value?.$el && content) {
        const el = passwordRef.value.$el as HTMLDivElement;
        instance?.destroy();
        instance = dbTippy(el, {
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
        }) as Instance;
      }
    },
  });


  const handlePasswordFocus = () => {
    instance?.show();
    passwordItemRef.value?.clearValidate();
  };

  const handlePasswordBlur = () => {
    instance?.hide();
  };

  const getStrenthStatus = (item: StrengthItem) => {
    if (!validate || Object.keys(validate).length === 0) {
      return '';
    }

    const isPass = item.keys.every((key) => {
      const verifyInfo = validate.value.password_verify_info || {};
      return verifyInfo[key as keyof PasswordStrengthVerifyInfo];
    });
    return `password-strength__status--${isPass ? 'success' : 'failed'}`;
  };

  const {
    run: createAccountRun,
  } = useRequest(createAccount, {
    manual: true,
    onSuccess() {
      Message({
        message: t('账号创建成功'),
        theme: 'success',
        delay: 1500,
      });
      emits('success');
      handleClose();
    },
    onAfter() {
      isLoading.value = false;
    },
  });

  const accountRef = ref();
  async function handleSubmit() {
    await accountRef.value.validate();

    isLoading.value = true;

    if (!publicKey) {
      await fetchRSAPublicKeys();
    }

    const params = {
      ...formData,
      password: getEncyptPassword(),
      account_type: TENDBCLUSTER,
    };

    createAccountRun(params, currentBizId);
  }

  const handleClose = () => {
    isShow.value = false;
    formData.password = '';
    formData.user = '';
    instance?.destroy();
    instance = null;
    validate.value = {} as PasswordStrength;
    strength.value = [];
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
