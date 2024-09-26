<template>
  <BkDialog
    class="account-dialog"
    :draggable="false"
    :esc-close="false"
    :is-show="accountDialogIsShow"
    :quick-close="false"
    :title="t('新建账号')"
    :width="580"
    @closed="handleClose">
    <BkForm
      v-if="accountDialogIsShow"
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
            content: userPlaceholder,
          }"
          :maxlength="32"
          :placeholder="userPlaceholder"
          show-word-limit />
        <p style="color: #ff9c01">
          {{ t('账号创建后，不支持修改。') }}
        </p>
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
            :disabled="isLoading"
            outline
            theme="primary"
            @click="handleAutoGeneration">
            {{ t('随机生成') }}
          </BkButton>
        </div>
        <p style="color: #ff9c01">
          {{ t('平台不会保存密码，请自行保管好。') }}
          <BkButton
            v-bk-tooltips="{
              content: t('请设置密码'),
              disabled: formData.password,
            }"
            class="copy-password-button"
            :disabled="!formData.password"
            text
            theme="primary"
            @click="handleCopyPassword">
            {{ t('复制密码') }}
          </BkButton>
        </p>
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
        v-for="(item, index) of passwordStrength"
        :key="index"
        class="password-strength-item">
        <span
          class="password-strength-status"
          :class="[getStrenthStatus(item)]" />
        <span class="password-strength-content">{{ item.text }}</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="tsx">
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
  import { createSqlserverAccount } from '@services/source/sqlserverPermissionAccount';

  import { useCopy } from '@hooks';

  import { AccountTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import { messageSuccess } from '@utils';

  interface Emits {
    (e: 'success'): void;
  }

  interface StrengthItem {
    keys: string[];
    text: string;
  }

  type PasswordStrengthVerifyInfo = PasswordStrength['password_verify_info'];

  type PasswordStrength = ServiceReturnType<typeof verifyPasswordStrength>;

  const emits = defineEmits<Emits>();

  const accountDialogIsShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const copy = useCopy();

  const passwordStrength = ref<StrengthItem[]>([]);
  const passwordRef = ref();
  const accountRef = ref();
  const passwordItemRef = ref();
  const passwordInstance = ref<Instance | null>();
  const publicKey = ref('');

  const passwordValidate = ref<PasswordStrength>({
    is_strength: false,
    password_verify_info: {} as PasswordStrengthVerifyInfo,
  });

  const formData = reactive({
    password: '',
    user: '',
  });

  const userPlaceholder = t('由_1_~_32_位字母_数字_下划线(_)_点(.)_减号(-)字符组成以字母或数字开头');

  /**
   * 远程校验密码是否符合要求
   */
  const verifyPassword = async () => {
    const passwordStrengthResult = await verifyPasswordStrength({
      password: getEncryptPassword(),
    });
    passwordValidate.value = passwordStrengthResult;
    return passwordStrengthResult.is_strength;
  };

  const debounceVerifyPassword = _.debounce(verifyPassword, 300);

  const rules = {
    user: [
      {
        trigger: 'change',
        message: userPlaceholder,
        validator: (value: string) => /^[a-zA-Z0-9][a-zA-Z0-9-_.]{0,31}$/.test(value),
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

  const passwordKeys = [
    {
      value: 'lowercase',
      label: t('包含小写字母'),
    },
    {
      value: 'uppercase',
      label: t('包含大写字母'),
    },
    {
      value: 'numbers',
      label: t('包含数字'),
    },
    {
      value: 'symbols',
      label: t('包含特殊字符，除空格外'),
    },
  ];

  const passwordSpecialKeys = [
    {
      value: 'keyboards',
      label: t('键盘序'),
    },
    {
      value: 'letters',
      label: t('字母序'),
    },
    {
      value: 'numbers',
      label: t('数字序'),
    },
    {
      value: 'symbols',
      label: t('特殊符号序'),
    },
  ];

  const { run: getRandomPasswordRun } = useRequest(getRandomPassword, {
    manual: true,
    onSuccess(randomPasswordResult) {
      formData.password = randomPasswordResult.password;
    },
  });

  const { run: runGetPasswordPolicy } = useRequest(getPasswordPolicy, {
    manual: true,
    onSuccess(passwordPolicyResult) {
      const {
        min_length: minLength,
        max_length: maxLength,
        include_rule: includeRule,
        exclude_continuous_rule: excludeContinuousRule,
      } = passwordPolicyResult.rule;
      passwordStrength.value = [
        {
          keys: ['min_length_valid', 'max_length_valid'],
          text: t('密码长度为_min_max', [minLength, maxLength]),
        },
      ];

      // 常规提示
      passwordKeys.forEach((item) => {
        if (item.value in includeRule) {
          passwordStrength.value.push({
            keys: [`${item.value}_valid`],
            text: item.label,
          });
        }
      });

      // 重复提示
      if (excludeContinuousRule.repeats) {
        passwordStrength.value.push({
          keys: ['repeats_valid'],
          text: t('不能连续重复n位字母_数字_特殊符号', { n: excludeContinuousRule.limit }),
        });
      }

      // 特殊提示（键盘序、字符序、数字序等）
      const keysMap: string[] = [];
      const labelMap = passwordSpecialKeys
        .map((item) => {
          if (item.value in excludeContinuousRule) {
            keysMap.push(`follow_${item.value}_valid`);
          }
          return item.label;
        })
        .join('、');
      if (keysMap.length && labelMap.length) {
        passwordStrength.value.push({
          keys: keysMap,
          text: labelMap,
        });
      }

      // 设置 tips
      const template = document.getElementById('passwordStrength');
      const content = template?.querySelector?.('.password-strength');
      const el = passwordRef.value.$el as HTMLDivElement;
      if (el && content) {
        passwordInstance.value?.destroy();
        passwordInstance.value = dbTippy(el, {
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
    },
  });

  const { run: runGetRSAPublicKeys } = useRequest(getRSAPublicKeys, {
    manual: true,
    onSuccess(RSAPublicKeysResult) {
      publicKey.value = RSAPublicKeysResult[0]?.content || '';
    },
  });

  const { loading: isLoading, run: runCreateAccount } = useRequest(createSqlserverAccount, {
    manual: true,
    onSuccess() {
      messageSuccess(t('账号创建成功'));
      emits('success');
      handleClose();
    },
  });

  watch(accountDialogIsShow, (show: boolean) => {
    if (show) {
      fetchPasswordPolicy();
      fetchRSAPublicKeys();
      passwordValidate.value = {} as PasswordStrength;
      passwordStrength.value = [];
    }
  });

  /**
   * 校验密码
   */
  watch(
    () => formData.password,
    (newPassword) => {
      if (newPassword) {
        debounceVerifyPassword();
      }
    },
  );

  /**
   * 自动生成密码
   */
  const handleAutoGeneration = () => {
    getRandomPasswordRun();
  };

  /**
   * 复制密码
   */
  const handleCopyPassword = () => {
    copy(formData.password);
  };

  /**
   * 获取加密密码
   */
  const getEncryptPassword = () => {
    const encypt = new JSEncrypt();
    encypt.setPublicKey(publicKey.value);
    const encyptPassword = encypt.encrypt(formData.password);
    return (typeof encyptPassword === 'string' && encyptPassword) || '';
  };

  /**
   * 获取公钥
   */
  const fetchRSAPublicKeys = () => {
    runGetRSAPublicKeys({ names: ['password'] });
  };

  /**
   * 校验密码当前项 并添加样式
   */
  const getStrenthStatus = (item: StrengthItem) => {
    if (!passwordValidate.value || !Object.keys(passwordValidate.value).length) {
      return '';
    }
    const isPass = item.keys.every((key) => {
      const verifyInfo = passwordValidate.value.password_verify_info || {};
      return verifyInfo[key as keyof PasswordStrengthVerifyInfo];
    });
    return `password-strength-status-${isPass ? 'success' : 'failed'}`;
  };

  const handleClose = () => {
    accountDialogIsShow.value = false;
    Object.assign(formData, {
      password: '',
      user: '',
    });
    passwordInstance.value?.destroy();
    passwordInstance.value = null;
    passwordValidate.value = {} as PasswordStrength;
    passwordStrength.value = [];
  };

  /**
   * 密码框获取焦点
   */
  const handlePasswordFocus = () => {
    passwordInstance.value?.show();
    // 清除校验信息
    passwordItemRef.value?.clearValidate();
  };

  /**
   * 密码框失去焦点
   */
  const handlePasswordBlur = () => {
    passwordInstance.value!.hide();
  };

  /**
   * 获取密码安全策略
   */
  const fetchPasswordPolicy = () => {
    runGetPasswordPolicy();
  };

  /**
   * 提交表单数据
   */
  const handleSubmit = async () => {
    await accountRef.value.validate();
    runCreateAccount({
      password: getEncryptPassword(),
      user: formData.user,
      account_type: AccountTypes.SQLSERVER,
    });
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .account-dialog {
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

    .copy-password-button {
      --disable-color: #c4c6cc;
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

    .password-strength-item {
      padding-bottom: 4px;
      .flex-center();
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

  .password-input {
    justify-content: space-between;
    align-items: center;
    display: flex;
  }
</style>
