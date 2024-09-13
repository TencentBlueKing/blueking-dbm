<template>
  <BkFormItem
    :label="t('访问密码')"
    :property="property"
    required
    :rule="passwordRuleList">
    <BkComposeFormItem>
      <BkInput
        ref="passwordRef"
        v-model="modelValue"
        class="password-input"
        style="width: 350px"
        type="password"
        @blur="handlePasswordBlur"
        @focus="handlePasswordFocus" />
      <BkButton
        class="form-item-suffix"
        outline
        theme="primary"
        @click="randomlyGenerate">
        {{ t('自动生成') }}
      </BkButton>
    </BkComposeFormItem>
  </BkFormItem>
  <div
    id="passwordStrength"
    class="password-strength-wrapper">
    <div class="password-strength">
      <div
        v-for="(item, index) of passwordStrength"
        :key="index"
        class="password-strength-item">
        <span
          class="password-strength-status"
          :class="[getStrenthStatus(item)]" />
        <span>{{ item.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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
  } from '@services/source/permission';

  import { dbTippy } from '@common/tippy';

  interface StrengthItem {
    keys: string[];
    text: string;
  }
  type PasswordPolicyKeys = keyof typeof PASSWORD_POLICY;
  type PasswordPolicy = ServiceReturnType<typeof getPasswordPolicy>;
  type PasswordStrength = ServiceReturnType<typeof verifyPasswordStrength>;

  interface Props {
    property: string;
  }

  defineProps<Props>();
  const modelValue = defineModel({
    required: true,
    default: '',
  });

  const { t } = useI18n();

  const verifyPassword = () =>
    verifyPasswordStrength({
      password: getEncyptPassword(),
    }).then((verifyResult) => {
      passwordValidate.value = verifyResult;
      return verifyResult.is_strength;
    });

  const debounceVerifyPassword = _.debounce(verifyPassword, 300);

  const getEncyptPassword = () => {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(publicKey);
    const encyptPassword = encypt.encrypt(modelValue.value);
    return typeof encyptPassword === 'string' ? encyptPassword : '';
  };

  const passwordKeys: string[] = [];
  const passwordFollowKeys: string[] = [];
  let instance: Instance | null = null;
  let publicKey = '';

  const PASSWORD_POLICY = {
    lowercase: t('包含小写字母'),
    uppercase: t('包含大写字母'),
    numbers: t('包含数字'),
    symbols: t('包含特殊字符_除空格外'),
    follow_keyboards: t('键盘序'),
    follow_letters: t('字母序'),
    follow_numbers: t('数字序'),
    follow_symbols: t('特殊符号序'),
  };

  const passwordRuleList = [
    {
      trigger: 'blur',
      message: t('密码不满足要求'),
      validator: debounceVerifyPassword,
    },
  ];

  Object.keys(PASSWORD_POLICY).forEach((key) => {
    if (key.includes('follow_')) {
      passwordFollowKeys.push(key);
    } else {
      passwordKeys.push(key);
    }
  });

  const passwordStrength = ref<StrengthItem[]>([]);
  const passwordValidate = ref({} as PasswordStrength);
  const passwordRef = ref();
  const passwordItemRef = ref();

  useRequest(getRSAPublicKeys, {
    defaultParams: [{ names: ['password'] }],
    onSuccess(publicKeyRes) {
      publicKey = publicKeyRes[0]?.content || '';
    },
  });

  useRequest(getPasswordPolicy, {
    onSuccess(passwordPolicyRes) {
      const {
        min_length: minLength,
        max_length: maxLength,
        include_rule: includeRule,
        exclude_continuous_rule: excludeContinuousRule,
      } = passwordPolicyRes.rule;

      passwordStrength.value = [
        {
          keys: ['min_length_valid', 'max_length_valid'],
          text: t('密码长度为_min_max', [minLength, maxLength]),
        },
      ];

      for (const passwordKey of passwordKeys) {
        if (includeRule[passwordKey as keyof PasswordPolicy['rule']['include_rule']]) {
          passwordStrength.value.push({
            keys: [`${passwordKey}_valid`],
            text: PASSWORD_POLICY[passwordKey as PasswordPolicyKeys],
          });
        }
      }

      if (excludeContinuousRule.repeats) {
        passwordStrength.value.push({
          keys: ['repeats_valid'],
          text: t('不能连续重复n位字母_数字_特殊符号', { n: excludeContinuousRule.limit }),
        });
      }

      const special = passwordFollowKeys.reduce((values: StrengthItem[], passwordFollowKey: string) => {
        const valueKey = passwordFollowKey.replace(
          'follow_',
          '',
        ) as keyof PasswordPolicy['rule']['exclude_continuous_rule'];
        if (excludeContinuousRule[valueKey]) {
          values.push({
            keys: [`${passwordFollowKey}_valid`],
            text: PASSWORD_POLICY[passwordFollowKey as PasswordPolicyKeys],
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
        passwordStrength.value.push({
          keys,
          text: texts.join('、'),
        });
      }

      const template = document.getElementById('passwordStrength');
      const content = template?.querySelector?.('.password-strength');
      if (passwordRef.value?.$el && content) {
        const el = passwordRef.value.$el as HTMLDivElement;
        instance?.destroy();
        instance = dbTippy(el, {
          trigger: 'manual',
          delay: 100000000,
          theme: 'light',
          content,
          arrow: true,
          placement: 'top-end',
          interactive: true,
          allowHTML: true,
          hideOnClick: false,
          zIndex: 9999,
          onDestroy: () => template?.append?.(content),
          appendTo: () => document.body,
        });
      }
    },
  });

  const { run: getRandomPasswordRun } = useRequest(getRandomPassword, {
    manual: true,
    onSuccess(randomPasswordRes) {
      modelValue.value = randomPasswordRes.password;
    },
  });

  watch(modelValue, () => {
    if (modelValue.value) {
      debounceVerifyPassword();
    }
  });

  const randomlyGenerate = () => {
    getRandomPasswordRun({
      security_type: 'redis_password',
    });
  };

  const handlePasswordFocus = () => {
    instance?.show();
    passwordItemRef.value?.clearValidate();
  };

  const handlePasswordBlur = () => {
    instance?.hide();
  };

  const getStrenthStatus = (item: StrengthItem) => {
    if (!passwordValidate.value || Object.keys(passwordValidate.value).length === 0) {
      return '';
    }

    const isPass = item.keys.every((key) => {
      const verifyInfo = passwordValidate.value.password_verify_info || {};
      return verifyInfo[key as keyof PasswordStrength['password_verify_info']];
    });
    return `password-strength-status-${isPass ? 'success' : 'failed'}`;
  };
</script>

<style lang="less" scoped>
  .password-input {
    border-right: none;
  }

  .password-strength-wrapper {
    position: relative;
    z-index: -1;
    display: none;
  }

  .password-strength {
    padding-top: 4px;
    font-size: @font-size-mini;

    .password-strength-item {
      display: flex;
      padding-bottom: 4px;
      align-items: center;
    }

    .password-strength-status {
      width: 6px;
      height: 6px;
      margin-right: 8px;
      background-color: @bg-disable;
      border-radius: 50%;
    }

    .password-strength-status-success {
      background-color: @bg-success;
    }

    .password-strength-status-failed {
      background-color: @bg-danger;
    }
  }
</style>
