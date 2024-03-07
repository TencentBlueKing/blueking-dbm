<template>
  <BkFormItem
    :label="t('统一临时密码')"
    property="password"
    required
    :rules="rules">
    <BkLoading :loading="isRSAPublicKeysLoading || isPasswordPolicyLoading">
      <BkComposeFormItem>
        <BkInput
          ref="passwordInputRef"
          v-model="modelValue"
          style="width: 300px"
          type="password"
          @blur="handlePasswordBlur"
          @focus="handlePasswordFocus" />
        <BkButton
          class="form-item-suffix"
          :loading="isRandomPasswordLoading"
          outline
          theme="primary"
          @click="handleRandomlyGenerate">
          {{ t('随机生成') }}
        </BkButton>
      </BkComposeFormItem>
    </BkLoading>
  </BkFormItem>
  <div
    ref="passwordRuleTipsRef"
    class="temporart-password-modify-tips">
    <div class="password-strength">
      <div
        v-for="(item, index) of passwordRuleTipList"
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
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getPasswordPolicy,
    getRandomPassword,
    getRSAPublicKeys,
    verifyPasswordStrength,
  } from '@services/source/permission';

  const encypt = new JSEncrypt();

  type PasswordPolicy = ServiceReturnType<typeof getPasswordPolicy>;
  type PasswordStrength = ServiceReturnType<typeof verifyPasswordStrength>;

  interface StrengthItem {
    keys: string[];
    text: string;
  }

  const { t } = useI18n();

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

  let tippyInstance: Instance | null;

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

  const modelValue = defineModel<string>({
    required: true,
  });

  const passwordInputRef = ref();
  const passwordRuleTipsRef = ref();
  const passwordRuleTipList = ref<
    {
      keys: string[];
      text: string;
    }[]
  >([]);
  const passwordValidate = ref({} as PasswordStrength);

  const rules = [
    {
      trigger: 'blur',
      message: t('密码不满足要求'),
      validator: () =>
        verifyPasswordStrength({
          password: encypt.encrypt(modelValue.value) || '',
        }).then((verifyResult) => {
          if (!verifyResult.is_strength && tippyInstance) {
            tippyInstance.show();
          }
          return verifyResult.is_strength;
        }),
    },
  ];

  const { loading: isRSAPublicKeysLoading } = useRequest(getRSAPublicKeys, {
    defaultParams: [
      {
        names: ['password'],
      },
    ],
    onSuccess(result) {
      encypt.setPublicKey(result[0]?.content || '');
    },
  });

  const { loading: isPasswordPolicyLoading } = useRequest(getPasswordPolicy, {
    onSuccess(result) {
      const {
        min_length: minLength,
        max_length: maxLength,
        include_rule: includeRule,
        exclude_continuous_rule: excludeContinuousRule,
      } = result.rule;

      passwordRuleTipList.value = [
        {
          keys: ['min_length_valid', 'max_length_valid'],
          text: t('密码长度为_min_max', [minLength, maxLength]),
        },
      ];

      const passwordKeys: string[] = [];
      const passwordFollowKeys: string[] = [];

      Object.keys(PASSWORD_POLICY).forEach((key) => {
        if (key.includes('follow_')) {
          passwordFollowKeys.push(key);
        } else {
          passwordKeys.push(key);
        }
      });

      for (const passwordKey of passwordKeys) {
        if (includeRule[passwordKey as keyof PasswordPolicy['rule']['include_rule']]) {
          passwordRuleTipList.value.push({
            keys: [`${passwordKey}_valid`],
            text: PASSWORD_POLICY[passwordKey as keyof typeof PASSWORD_POLICY],
          });
        }
      }

      if (excludeContinuousRule.repeats) {
        passwordRuleTipList.value.push({
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
            text: PASSWORD_POLICY[passwordFollowKey as keyof typeof PASSWORD_POLICY],
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
        passwordRuleTipList.value.push({
          keys,
          text: texts.join('、'),
        });
      }
    },
  });

  const { loading: isRandomPasswordLoading, run: getRandomPasswordRun } = useRequest(getRandomPassword, {
    manual: true,
    onSuccess(randomPasswordRes) {
      modelValue.value = randomPasswordRes.password;
    },
  });

  const { run: runVerifyPasswordStrength } = useRequest(verifyPasswordStrength, {
    manual: true,
    onSuccess(result) {
      passwordValidate.value = result;
    },
  });

  watch(modelValue, () => {
    runVerifyPasswordStrength({
      password: encypt.encrypt(modelValue.value) || '',
    });
  });

  const handlePasswordFocus = () => {
    tippyInstance?.show();
  };

  const handlePasswordBlur = () => {
    tippyInstance?.hide();
  };

  const handleRandomlyGenerate = () => {
    getRandomPasswordRun();
  };

  onMounted(() => {
    tippyInstance = tippy(passwordInputRef.value.$el as SingleTarget, {
      content: passwordRuleTipsRef.value,
      trigger: 'manual',
      theme: 'light',
      arrow: true,
      placement: 'top-end',
      interactive: true,
      allowHTML: true,
      hideOnClick: false,
      zIndex: 9999,
      appendTo: () => document.body,
    });
  });

  onBeforeUnmount(() => {
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.destroy();
    }
  });
</script>
<style lang="less" scoped>
  .temporart-password-modify-tips {
    .password-strength {
      min-width: 180px;
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
  }
</style>
