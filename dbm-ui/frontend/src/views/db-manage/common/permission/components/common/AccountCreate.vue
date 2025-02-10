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
    :is-show="isShow"
    :quick-close="false"
    :title="t('新建账号')"
    :width="580"
    @closed="handleClose">
    <BkForm
      v-if="isShow"
      ref="accountRef"
      form-type="vertical"
      :model="state.formdata"
      :rules="rules">
      <BkFormItem
        :label="t('账户名')"
        property="user"
        required>
        <BkInput
          v-model="state.formdata.user"
          v-bk-tooltips="{
            trigger: 'click',
            placement: 'top-start',
            theme: 'light',
            content: userPlaceholder,
          }"
          :maxlength="32"
          :placeholder="userPlaceholder"
          show-word-limit />
      </BkFormItem>
      <div class="account-dialog-explain">
        {{ t('账号创建后，不支持修改。') }}
      </div>
      <BkFormItem
        :label="t('密码')"
        property="password"
        required>
        <PasswordInput
          ref="passwordRef"
          v-model="state.formdata.password"
          :db-type="dbTypeMap[accountType]"
          @verify-result="verifyResult" />
      </BkFormItem>
      <div class="account-dialog-explain">
        {{ t('平台不会保存密码，请自行保管好。') }}
        <BkButton
          v-bk-tooltips="{
            content: t('请设置密码'),
            disabled: state.formdata.password,
          }"
          class="copy-password-button"
          :disabled="!state.formdata.password"
          text
          theme="primary"
          @click="handleCopyPassword">
          {{ t('复制密码') }}
        </BkButton>
      </div>
    </BkForm>
    <template #footer>
      <BkButton
        v-bk-tooltips="{
          content: t('密码不符合要求'),
          disabled: !Boolean(state.formdata.password) || passwordIsPass,
        }"
        class="mr-8"
        :disabled="!passwordIsPass"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { createAccount as createMongodbAccount } from '@services/source/mongodbPermissionAccount';
  import { createAccount as createMysqlAccount } from '@services/source/mysqlPermissionAccount';
  import { createAccount as createSqlserverAccount } from '@services/source/sqlserverPermissionAccount';

  import { AccountTypes, DBTypes } from '@common/const';

  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';

  import { execCopy } from '@utils';

  import MongoConfig from '../mongo/config';
  import MysqlConfig from '../mysql/config';
  import SqlserverConfig from '../sqlserver/config';

  interface Props {
    accountType: AccountTypes;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();

  const dbTypeMap = {
    [AccountTypes.MYSQL]: DBTypes.MYSQL,
    [AccountTypes.TENDBCLUSTER]: DBTypes.TENDBCLUSTER,
    [AccountTypes.SQLSERVER]: DBTypes.SQLSERVER,
    [AccountTypes.MONGODB]: DBTypes.MONGODB,
  };

  const state = reactive({
    formdata: {
      password: '',
      user: '',
    },
    isLoading: false,
    publicKey: '',
  });
  const accountRef = ref();
  const passwordRef = ref<InstanceType<typeof PasswordInput>>();
  const passwordIsPass = ref(false);

  const defaultUserPlaceholder = t('由_1_~_32_位字母_数字_下划线(_)_点(.)_减号(-)字符组成以字母或数字开头');
  let validValue = '';

  const userPlaceholder = computed(() => {
    if (props.accountType === AccountTypes.MONGODB) {
      return t('格式为：(库名).（名称）_如 admin.linda');
    }
    return defaultUserPlaceholder;
  });

  const rules = computed(() => ({
    user: [
      {
        trigger: 'blur',
        message: t('账户名不能为空'),
        validator: (value: string) => !!value,
      },
      {
        trigger: 'blur',
        message: defaultUserPlaceholder,
        validator: (value: string) => /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,31}$/g.test(value),
      },
      props.accountType === AccountTypes.MONGODB
        ? {
            trigger: 'blur',
            message: userPlaceholder.value,
            validator: (value: string) => /^([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)$/g.test(value),
          }
        : {},
      {
        trigger: 'blur',
        validator: (value: string) => {
          const specialAccountMap = {
            [AccountTypes.MYSQL]: MysqlConfig[AccountTypes.MYSQL].special_account,
            [AccountTypes.TENDBCLUSTER]: MysqlConfig[AccountTypes.TENDBCLUSTER].special_account,
            [AccountTypes.MONGODB]: MongoConfig.special_account,
            [AccountTypes.SQLSERVER]: SqlserverConfig.special_account,
          };
          validValue = props.accountType === AccountTypes.MONGODB ? value.split('.')[1] : value;
          return !specialAccountMap[props.accountType].includes(validValue);
        },
        message: () => t('不允许使用特殊账号名称n', { n: validValue }),
      },
    ],
    password: [
      {
        trigger: 'blur',
        message: t('密码不能为空'),
        validator: (value: string) => !!value,
      },
      {
        trigger: 'blur',
        message: t('密码不满足要求'),
        validator: () => passwordRef.value!.validate(),
      },
    ],
  }));

  /**
   * 复制密码
   */
  const handleCopyPassword = () => {
    execCopy(state.formdata.password, t('复制成功，共n条', { n: 1 }));
  };

  const verifyResult = (isPass: boolean) => {
    passwordIsPass.value = isPass;
  };

  /**
   * 提交表单数据
   */
  const handleSubmit = async () => {
    await accountRef.value.validate();
    state.isLoading = true;

    const password = passwordRef.value!.getEncyptPassword();
    const apiMap = {
      [AccountTypes.MYSQL]: createMysqlAccount,
      [AccountTypes.TENDBCLUSTER]: createMysqlAccount,
      [AccountTypes.MONGODB]: createMongodbAccount,
      [AccountTypes.SQLSERVER]: createSqlserverAccount,
    };
    apiMap[props.accountType]({
      ...state.formdata,
      password,
      account_type: props.accountType,
    })
      .then(() => {
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
  };

  /**
   * 关闭 dialog
   */
  const handleClose = () => {
    isShow.value = false;
    state.formdata.password = '';
    state.formdata.user = '';
  };
</script>

<style lang="less" scoped>
  .account-dialog {
    :deep(.bk-form-item) {
      margin-bottom: 0;
    }

    :deep(.is-error) {
      margin-bottom: 18px;
    }

    .account-dialog-explain {
      padding-top: 4px;
      margin-bottom: 16px;
      font-size: 12px;
      color: #ff9c01;
    }
  }
</style>
