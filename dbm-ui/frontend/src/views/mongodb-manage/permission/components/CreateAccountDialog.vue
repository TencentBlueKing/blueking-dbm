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
    <!-- <BkAlert
      class="mb-16"
      closable
      theme="warning"
      :title="t('账号名创建后_不支持修改_密码创建后平台将不会显露_请谨记')" /> -->
    <BkForm
      v-if="isShow"
      ref="accountRef"
      class="mongo-add-account mb-36"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <BkFormItem
        :label="t('账户名')"
        property="user"
        required>
        <BkPopover
          allow-html
          content="#account-pop"
          placement="right"
          render-type="auto"
          theme="light"
          trigger="click">
          <BkInput
            v-model="formData.user"
            :placeholder="t('格式为：(库名).（名称）_如 admin.linda')" />
        </BkPopover>
      </BkFormItem>
      <BkFormItem
        ref="passwordItemRef"
        :label="t('密码')"
        property="password"
        required>
        <div class="password-item">
          <BkInput
            ref="passwordRef"
            v-model="formData.password"
            class="password-input"
            :placeholder="t('请输入')"
            type="password"
            @blur="handlePasswordBlur"
            @focus="handlePasswordFocus" />
          <BkButton
            class="password-generate-button"
            outline
            theme="primary"
            @click="randomlyGenerate">
            {{ t('随机生成') }}
          </BkButton>
        </div>
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
  <div style="display: none;">
    <div
      id="account-pop"
      class="mongo-account-pop">
      <p>{{ t('格式为：(库名).（名称）_如 admin.linda') }}</p>
      <p class="mongo-account-pop-text">
        {{ t('由 1～32 位字母、数字、下划线(_)、点(.)、减号(-)字符组成以字母或数字开头') }}
      </p>
    </div>
  </div>
  <div id="passwordStrength">
    <div class="mongo-password-strength">
      <div
        v-for="(item, index) of strength"
        :key="index"
        class="strength-item">
        <span
          class="strength-status"
          :class="[getStrenthStatus(item)]" />
        <span>{{ item.text }}</span>
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

  import {
    getPasswordPolicy,
    getRandomPassword,
    getRSAPublicKeys,
    verifyPasswordStrength,
  } from '@services/permission';
  import { createMongodbAccount } from '@services/source/mongodbPermissionAccount';

  import { AccountTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import {
    PASSWORD_POLICY,
    type PasswordPolicyKeys,
  } from '../common/consts';

  import { useGlobalBizs } from '@/stores';

  type PasswordPolicy = ServiceReturnType<typeof getPasswordPolicy>;
  type PasswordStrength = ServiceReturnType<typeof verifyPasswordStrength>;

  interface StrengthItem {
    keys: string[],
    text: string
  }

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

  let instance: Instance | null = null;
  let publicKey = '';
  const keys: string[] = [];
  const followKeys: string[] = [];

  Object.keys(PASSWORD_POLICY).forEach((key) => {
    if (key.includes('follow_')) {
      followKeys.push(key);
    } else {
      keys.push(key);
    }
  });

  const formData = reactive({
    password: '',
    user: '',
  });
  const isLoading = ref(false);
  const strength = ref<StrengthItem[]>([]);
  const validate = ref({} as PasswordStrength);
  const passwordRef = ref();
  const passwordItemRef = ref();
  const accountRef = ref();

  const verifyPassword = () => verifyPasswordStrength({
    password: getEncyptPassword(),
  })
    .then((res) => {
      validate.value = res;
      return res.is_strength;
    });

  const debounceVerifyPassword = _.debounce(verifyPassword, 300);
  const rules = {
    user: [
      {
        trigger: 'change',
        message: t('由 1～32 位字母、数字、下划线(_)、点(.)、减号(-)字符组成以字母或数字开头'),
        validator: (value: string) => /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,31}$/g.test(value),
      },
      {
        trigger: 'change',
        message: t('格式为：(库名).（名称）_如 admin.linda'),
        validator: (value: string) => /^[^/.].*[^/.]$/g.test(value),
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

  const {
    run: getRandomPasswordRun,
  } = useRequest(getRandomPassword, {
    manual: true,
    onSuccess(randomPasswordRes) {
      formData.password = randomPasswordRes.password;
    },
  });

  const { run: fetchPasswordPolicy } = useRequest(getPasswordPolicy, {
    manual: true,
    onSuccess(res) {
      const {
        min_length: minLength,
        max_length: maxLength,
        include_rule: includeRule,
        exclude_continuous_rule: excludeContinuousRule,
      } = res.rule;

      strength.value = [{
        keys: ['min_length_valid', 'max_length_valid'],
        text: t('密码长度为_min_max', [minLength, maxLength]),
      }];

      // 常规提示
      for (const key of keys) {
        if (includeRule[key as keyof PasswordPolicy['rule']['include_rule']]) {
          strength.value.push({
            keys: [`${key}_valid`],
            text: t(PASSWORD_POLICY[key as PasswordPolicyKeys]),
          });
        }
      }

      // 重复提示
      if (excludeContinuousRule.repeats) {
        strength.value.push({
          keys: ['repeats_valid'],
          text: t('不能连续重复n位字母_数字_特殊符号', { n: excludeContinuousRule.limit }),
        });
      }

      // 特殊提示（键盘序、字符序、数字序等）
      const special = followKeys.reduce((values, key: string) => {
        const valueKey = key.replace('follow_', '') as keyof PasswordPolicy['rule']['exclude_continuous_rule'];
        if (excludeContinuousRule[valueKey]) {
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
      const content = template?.querySelector?.('.mongo-password-strength');
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

  const {
    run: createAccountRun,
  } = useRequest(createMongodbAccount, {
    manual: true,
    onSuccess() {
      Message({
        message: t('账号创建成功'),
        theme: 'success',
      });
      emits('success');
      handleClose();
    },
    onAfter() {
      isLoading.value = false;
    },
  });

  watch(isShow, (show: boolean) => {
    if (show) {
      fetchRSAPublicKeys();
      fetchPasswordPolicy();
      validate.value = {} as PasswordStrength;
      strength.value = [];
    }
  });

  watch(() => formData.password, (psw) => {
    psw && debounceVerifyPassword();
  });

  const randomlyGenerate = () => {
    getRandomPasswordRun();
  };

  const fetchRSAPublicKeys = () =>  {
    getRSAPublicKeys({ names: ['password'] })
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
      return verifyInfo[key as keyof PasswordStrength['password_verify_info']];
    });
    return `status-${isPass ? 'success' : 'failed'}`;
  };

  const handleSubmit = async () =>  {
    await accountRef.value.validate();

    isLoading.value = true;

    if (!publicKey) {
      await fetchRSAPublicKeys();
    }

    const params = {
      ...formData,
      password: getEncyptPassword(),
      account_type: AccountTypes.MONGODB,
      bizId: currentBizId,
    };

    createAccountRun(params);
  };

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
  .mongo-add-account {
    .password-item {
      display: flex;

      .password-input {
        border-right: none;
        border-radius: 2px 0 0 2px;
        flex: 1;
      }

      .password-generate-button {
        border-radius: 0 2px 2px 0;
      }
    }
  }
</style>

<style lang="less">
  .mongo-account-pop {
    color: #63656E;

    .mongo-account-pop-text {
      margin-top: 4px;
    }
  }

  .mongo-password-strength {
    padding-top: 4px;
    font-size: @font-size-mini;

    .strength-item {
      display: flex;
      padding-bottom: 4px;
      align-items: center;
    }

    .strength-status {
      width: 6px;
      height: 6px;
      margin-right: 8px;
      background-color: @bg-disable;
      border-radius: 50%;
    }

    .status-success {
      background-color: @bg-success;
    }

    .status-failed {
      background-color: @bg-danger;
    }
  }
</style>
