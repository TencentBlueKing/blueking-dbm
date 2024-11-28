<template>
  <div class="password-form-item">
    <BkInput
      ref="passwordInputRef"
      v-model="modelValue"
      class="password-input"
      :placeholder="t('请输入')"
      type="password"
      @blur="handlePasswordBlur"
      @focus="handlePasswordFocus" />
    <BkButton
      v-bk-tooltips="{
        content: buttonDisabledTip,
        disabled: !buttonDisabled,
      }"
      class="password-generate-button"
      :disabled="isLoading || buttonDisabled"
      outline
      theme="primary"
      @click="handleAutoGeneration">
      {{ t('自动生成') }}
    </BkButton>
  </div>
  <div
    id="passwordStrength"
    class="password-strength-wrapper">
    <div class="password-strength">
      <div
        v-for="(item, key) of strength"
        :key="key"
        class="password-strength-item">
        <span
          class="password-strength-status"
          :class="[getStrenthStatus(item.keys)]" />
        <span class="password-strength-content">{{ item.text }}</span>
      </div>
      <div
        v-for="(item, key) of appendTips"
        :key="key"
        class="password-strength-item">
        <span class="password-strength-status password-strength-status--failed" />
        <span class="password-strength-content">{{ item }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import JSEncrypt from 'jsencrypt';
  import _ from 'lodash';
  import { type Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getPasswordPolicy,
    getRandomPassword,
    getRSAPublicKeys,
    verifyPasswordStrength,
  } from '@services/source/permission';

  import { DBTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  type PasswordPolicy = ServiceReturnType<typeof getPasswordPolicy>;
  type PasswordStrengthVerifyInfo = ServiceReturnType<typeof verifyPasswordStrength>['password_verify_info'];

  interface Props {
    dbType?: DBTypes;
    buttonDisabled?: boolean;
    buttonDisabledTip?: string;
  }

  interface Emits {
    (e: 'verifyResult', isPass: boolean): void;
  }

  interface Exposes {
    getEncyptPassword: () => string;
    validate: () => Promise<boolean>;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
    buttonDisabled: false,
    buttonDisabledTip: '',
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>('modelValue', {
    default: '',
  });

  const { t } = useI18n();

  let tippyInstance: Instance;
  let publicKey = '';
  let passwordPolicyMemo = {} as PasswordPolicy['rule'];

  const passwordInputRef = ref();
  const strength = ref<
    Record<
      string,
      {
        keys: string[];
        text: string;
      }
    >
  >({});
  const appendTips = ref<Record<string, string>>({});
  const validate = ref<PasswordStrengthVerifyInfo>({
    number_of_types_valid: false,
    allowed_valid: false,
    out_of_range: '',
    repeats_valid: false,
    follow_keyboards_valid: false,
    follow_letters_valid: false,
    follow_numbers_valid: false,
    follow_symbols_valid: false,
    min_length_valid: false,
    max_length_valid: false,
  });

  const passwordParam = computed(() =>
    props.dbType === DBTypes.REDIS ? 'redis_password_v2' : `${props.dbType}_password`,
  );

  useRequest(getRSAPublicKeys, {
    defaultParams: [{ names: ['password'] }],
    onSuccess(publicKeyRes) {
      publicKey = publicKeyRes[0]?.content || '';
    },
  });

  useRequest(getPasswordPolicy, {
    defaultParams: [{ name: passwordParam.value }],
    onSuccess(data) {
      const {
        min_length: minLength,
        max_length: maxLength,
        include_rule: includeRule,
        number_of_types: numberOfType,
        symbols_allowed: symbolsAllowed,
      } = data.rule;

      passwordPolicyMemo = data.rule;

      const PASSWORD_POLICY = {
        lowercase: t('小写字母'),
        uppercase: t('大写字母'),
        numbers: t('数字'),
        symbols: t('指定特殊字符(s)', { s: symbolsAllowed }),
      };

      const texts = Object.entries(PASSWORD_POLICY).reduce<string[]>((acc, [key, text]) => {
        const valid = includeRule[key as keyof PasswordPolicy['rule']['include_rule']];

        if (!valid) {
          return acc;
        }

        return [...acc, t(text)];
      }, []);

      strength.value = {
        length: {
          keys: ['min_length_valid', 'max_length_valid'],
          text: t('密码长度为_min_max', [minLength, maxLength]),
        },
        number_of_types: {
          keys: ['number_of_types_valid'],
          text: t('包含') + texts.join('、') + t('中的任意 n 种', { n: numberOfType }),
        },
      };

      // 设置 tips
      const template = document.getElementById('passwordStrength');
      const content = template?.querySelector?.('.password-strength');
      if (passwordInputRef.value?.$el && content) {
        const el = passwordInputRef.value.$el as HTMLDivElement;
        tippyInstance?.destroy();
        tippyInstance = dbTippy(el, {
          trigger: 'manual',
          theme: 'light',
          content,
          arrow: true,
          placement: 'top-start',
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

  const { run: getRandomPasswordRun, loading: isLoading } = useRequest(getRandomPassword, {
    manual: true,
    onSuccess(data) {
      modelValue.value = data.password;
    },
  });

  watch(
    () => props.dbType,
    () => {
      modelValue.value = '';
    },
  );

  /**
   * 获取加密密码
   */
  const getEncyptPassword = () => {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(publicKey);
    const encyptPassword = encypt.encrypt(modelValue.value);
    return typeof encyptPassword === 'string' ? encyptPassword : '';
  };

  const { runAsync: verifyPasswordRun } = useRequest(verifyPasswordStrength, {
    manual: true,
    onSuccess(data) {
      appendTips.value = {};
      validate.value = data.password_verify_info;

      /**
       * 是否出现不允许的字符
       */
      if (!data.password_verify_info.allowed_valid) {
        appendTips.value.symbols_allowed = t('不允许的字符: s', { s: data.password_verify_info.out_of_range });
      }

      /**
       * 不允许超过x位连续字符，仅当弱密码检测开启时校验
       */
      const weakPasswordKeys = [
        'repeats_valid',
        'follow_letters_valid',
        'follow_symbols_valid',
        'follow_keyboards_valid',
        'follow_numbers_valid',
      ];
      const isPass = weakPasswordKeys.every(
        (key) => data.password_verify_info[key as keyof PasswordStrengthVerifyInfo],
      );
      if (!isPass) {
        appendTips.value.weak_password = t('不允许超过 x 位连续字符', { x: passwordPolicyMemo.repeats });
      }
    },
  });

  /**
   * 校验密码是否符合要求
   */
  const verifyPassword = async () => {
    const { is_strength: isStrength } = await verifyPasswordRun({
      security_type: passwordParam.value,
      password: getEncyptPassword(),
    });
    tippyInstance.show();
    emits('verifyResult', isStrength);
    return isStrength;
  };
  const debounceVerifyPassword = _.debounce(verifyPassword, 300);

  /**
   * 获取密码当前项是否校验
   */
  const getStrenthStatus = (keys: string[]) => {
    if (!validate.value || Object.keys(validate.value).length === 0) {
      return '';
    }
    const isPass = keys.every((key) => validate.value[key as keyof PasswordStrengthVerifyInfo]);
    return `password-strength-status--${isPass ? 'success' : 'failed'}`;
  };

  /**
   * 自动生成密码
   */
  const handleAutoGeneration = () => {
    getRandomPasswordRun({
      security_type: passwordParam.value,
    });
  };

  /**
   * 密码框获取焦点
   */
  const handlePasswordFocus = () => {
    debounceVerifyPassword();
  };

  /**
   * 密码框失去焦点
   */
  const handlePasswordBlur = () => {
    tippyInstance.hide();
  };

  watch(modelValue, () => {
    debounceVerifyPassword();
  });

  onUnmounted(() => {
    tippyInstance.destroy();
  });

  defineExpose<Exposes>({
    getEncyptPassword,
    validate: verifyPassword,
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .password-form-item {
    display: flex;

    .password-input {
      flex: 1;
      border-right: none;
      border-radius: 2px 0 0 2px;
    }

    .password-generate-button {
      border-radius: 0 2px 2px 0;
    }
  }

  .copy-password-button {
    --disable-color: #c4c6cc;
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
    }

    .password-strength-status {
      position: relative;
      top: 6px;
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

    .password-strength-content {
      width: 260px;
    }
  }
</style>
