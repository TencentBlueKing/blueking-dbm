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
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :title="isEdit ? t('编辑授权规则') : t('添加授权规则')"
    :width="840"
    @closed="handleClose">
    <DbForm
      ref="ruleRef"
      class="rule-form"
      form-type="vertical"
      :model="formdata"
      :rules="rules">
      <BkFormItem
        :label="t('账号名')"
        property="account_id"
        required>
        <BkSelect
          v-model="formdata.account_id"
          :clearable="false"
          :disabled="isEdit"
          filterable
          :input-search="false"
          :loading="isLoading">
          <BkOption
            v-for="item of accounts"
            :key="item.account_id"
            :label="item.user"
            :value="item.account_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('访问DB')"
        property="access_db"
        required
        :rules="rules.access_db">
        <BkInput
          v-model="formdata.access_db"
          :placeholder="t('请输入DB名称_可以使用通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔')"
          :rows="3"
          type="textarea" />
      </BkFormItem>
      <BkFormItem
        class="form-item privilege"
        :label="t('权限设置')"
        property="auth"
        :required="false">
        <div class="rule-setting-box">
          <BkFormItem
            label="DML"
            required>
            <div class="rule-form-row">
              <BkCheckbox
                v-bk-tooltips="{
                  content: t('你已选择所有权限'),
                  disabled: !checkAllPrivileges,
                }"
                class="check-all"
                :disabled="checkAllPrivileges"
                :indeterminate="getAllCheckedboxIndeterminate('dml')"
                :model-value="getAllCheckedboxValue('dml')"
                @change="(value: boolean) => handleSelectedAll('dml', value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formdata.privilege.dml"
                class="checkbox-group">
                <BkCheckbox
                  v-for="option of dbOperations.dml"
                  :key="option"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges || (isEdit && editModeDisabledPrivileges.includes(option))"
                  :label="option">
                  {{ option }}
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
          <BkFormItem
            label="DDL"
            required>
            <div class="rule-form-row">
              <BkCheckbox
                v-bk-tooltips="{
                  content: t('你已选择所有权限'),
                  disabled: !checkAllPrivileges,
                }"
                class="check-all"
                :disabled="checkAllPrivileges"
                :indeterminate="getAllCheckedboxIndeterminate('ddl')"
                :model-value="getAllCheckedboxValue('ddl')"
                @change="(value: boolean) => handleSelectedAll('ddl', value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formdata.privilege.ddl"
                class="checkbox-group">
                <BkCheckbox
                  v-for="option of dbOperations.ddl"
                  :key="option"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges || (isEdit && editModeDisabledPrivileges.includes(option))"
                  :label="option">
                  {{ option }}
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
          <BkFormItem
            :label="t('全局')"
            required>
            <div class="rule-form-row">
              <BkCheckbox
                v-bk-tooltips="{
                  content: t('你已选择所有权限'),
                  disabled: !checkAllPrivileges,
                }"
                class="check-all"
                :disabled="checkAllPrivileges"
                :indeterminate="getAllCheckedboxIndeterminate('glob')"
                :model-value="getAllCheckedboxValue('glob')"
                @change="(value: boolean) => handleSelectedAll('glob', value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formdata.privilege.glob"
                class="checkbox-group">
                <BkCheckbox
                  v-for="option of dbOperations.glob"
                  :key="option"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges || (isEdit && editModeDisabledPrivileges.includes(option))"
                  :label="option">
                  {{ option }}
                  <span class="sensitive-tip">{{ t('敏感') }}</span>
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
        </div>
        <!-- <div
          class="rule-setting-box"
          style="margin-top: 16px;">
          <BkFormItem
            class="mb-0"
            :label="t('所有权限')">
            <BkCheckbox
              :model-value="checkAllPrivileges"
              @change="(value: boolean) => handleSelectAllPrivileges(value)">
              all privileges（{{ t('包含所有权限，其他权限无需授予') }}）
            </BkCheckbox>
          </BkFormItem>
        </div> -->
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkPopConfirm
        :content="precheckWarnTip"
        :is-show="showPopConfirm"
        :title="t('确定提交？')"
        trigger="manual"
        width="400"
        @cancel="handleVerifyCancel"
        @confirm="handleVerifyConfirm">
        <BkButton
          class="w-88 mr-8"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { JSX } from 'vue/jsx-runtime';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import {
    createAccountRule,
    getPermissionRules,
    modifyAccountRule,
    preCheckAddAccountRule,
    queryAccountRules,
  } from '@services/source/permission';
  import type {
    AccountRule,
    PermissionRuleAccount,
  } from '@services/types/permission';

  import { useBeforeClose } from '@hooks';

  import { AccountTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import { dbOperations } from '../common/consts';

  type AuthItemKey = keyof typeof dbOperations;


  interface Props {
    accountId: number,
    ruleObj?: MysqlPermissonAccountModel['rules'][number];
  }

  interface Emits {
    (e: 'success'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    accountId: -1,
    ruleObj: undefined
  });

  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const replaceReg = /[,;\r\n]/g;

  const { TENDBCLUSTER } = AccountTypes;

  const initFormdata = (): AccountRule =>  ({
    account_id: null,
    access_db: '',
    privilege: {
      ddl: [],
      dml: [],
      glob: [],
    },
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const ruleRef = ref();
  const checkAllPrivileges = ref(false);
  const showPopConfirm = ref(false);
  const precheckWarnTip = ref<JSX.Element>();
  const formdata = ref(initFormdata());
  const accounts = ref<PermissionRuleAccount[]>([]);
  const isLoading = ref(false);
  const existDBs = ref<string[]>([]);
  const editModeDisabledPrivileges = ref<string[]>([])

  const isEdit = computed(() => !!props.ruleObj?.account_id);

  const selectedUserInfo = computed(() => accounts.value.find(item => item.account_id === formdata.value.account_id));

  const rules = {
    auth: [
      {
        trigger: 'change',
        message: t('请设置权限'),
        validator: () => {
          const { ddl, dml, glob } = formdata.value.privilege;
          return ddl.length !== 0 || dml.length !== 0 || glob.length !== 0 || checkAllPrivileges.value;
        },
      },
    ],
    access_db: [
      {
        required: true,
        trigger: 'blur',
        message: t('访问DB不能为空'),
        validator: (value: string) => !!value,
      },
      {
        trigger: 'blur',
        message: t('DB名称不支持 *'),
        validator: (value: string) => {
          const dbs = value.split(/[\n;,]/);
          return _.every(dbs, item => !item ? true: !/\*/.test(item))
        },
      },
      {
        trigger: 'blur',
        message: () => t('该账号下已存在xx规则', [existDBs.value.join('，')]),
        validator: async () => {
          existDBs.value = [];

          const user = selectedUserInfo.value?.user;
          const dbs = formdata.value.access_db.replace(replaceReg, ',')
            .split(',')
            .filter(db => db !== '');

          if (!user || dbs.length === 0) return false;

          const { results } = await queryAccountRules({
            bizId: window.PROJECT_CONFIG.BIZ_ID,
            user,
            access_dbs: dbs,
            account_type: TENDBCLUSTER,
          })
          const intersection = results.find(item => item.account.user === user)?.rules
            .filter(ruleItem => dbs.includes(ruleItem.access_db)) || [];
          existDBs.value = intersection.map(item => item.access_db);
          return !intersection.length;
        },
      },
    ],
  };

  const {
    loading: isSubmitting,
    run: createAccountRuleRun,
  } = useRequest(createAccountRule, {
    manual: true,
    onSuccess() {
      messageSuccess(t('成功添加授权规则'));
      emits('success');
      window.changeConfirm = false;
      handleClose();
    },
  });

  watch(isShow, (show) => {
    if (show) {
      formdata.value.account_id = props.accountId ?? -1;
      getAccount();

      if (isEdit.value) {
        formdata.value.access_db = props.ruleObj!.access_db;
        editModeDisabledPrivileges.value = props.ruleObj!.privilege.split(',');
        const dbOperationsMap = Object.entries(dbOperations).reduce((resultMap, [key, values]) => {
          values.forEach(value => {
            Object.assign(resultMap, { [value]: key });
          });
          return resultMap;
        }, {} as Record<string, string>);

        editModeDisabledPrivileges.value.forEach(privilege => {
          const key = dbOperationsMap[privilege] as keyof AccountRule['privilege'];
          if (!key) {
            return;
          }
          if (!formdata.value.privilege[key].includes(privilege)) {
            formdata.value.privilege[key].push(privilege);
          }
        })
      }
    }
  });

  const getAccount = () => {
    isLoading.value = true;
    getPermissionRules({
      offset: 0,
      limit: -1,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      account_type: TENDBCLUSTER,
    })
      .then((res) => {
        accounts.value = res.results.map(item => item.account);
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const getAllCheckedboxValue = (key: AuthItemKey) => formdata.value.privilege[key].length === dbOperations[key].length;

  const getAllCheckedboxIndeterminate = (key: AuthItemKey) => (
    formdata.value.privilege[key].length > 0
    && formdata.value.privilege[key].length !== dbOperations[key].length
  );

  const handleSelectedAll = (key: AuthItemKey, value: boolean) => {
    if (value) {
      formdata.value.privilege[key] = [...dbOperations[key]];
      return;
    }

    formdata.value.privilege[key] = [];
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();

    if (!result) return;

    isShow.value = false;
    formdata.value = initFormdata();
    checkAllPrivileges.value = false;
    existDBs.value = [];
    window.changeConfirm = false;
  };

  const handleVerifyCancel = () => {
    showPopConfirm.value = false;
    isSubmitting.value = false;
  };

  const generateRequestParam = () => {
    const formDataClone = _.cloneDeep(formdata.value);
    if (checkAllPrivileges.value) {
      // 包含所有权限
      formDataClone.privilege.glob = ['all privileges'];
    }

    return ({
      ...formDataClone,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      access_db: formdata.value.access_db.replace(replaceReg, ','), // 统一分隔符
      account_type: TENDBCLUSTER,
    });
  };

  const handleVerifyConfirm = () => {
    showPopConfirm.value = false;
    const params = generateRequestParam();
    createAccountRuleRun(params);
  };

  const handleSubmit = async () => {
    if (!isEdit.value) {
      await ruleRef.value.validate();
    }

    isSubmitting.value = true;
    const params = generateRequestParam();
    if (isEdit.value) {
      modifyAccountRule({
        ...params,
        rule_id: props.ruleObj!.rule_id,
      }).finally(() => {
        messageSuccess(t('编辑授权规则成功'));
        emits('success');
        isSubmitting.value = false;
        isShow.value = false;
      });
      return
    }
    preCheckAddAccountRule(params)
      .then((result) => {
        if (result.warning) {
          precheckWarnTip.value = (
            <div class="pre-check-content">
              {result.warning.split('\n').map(line => <div>{line}</div>)}
            </div>
          );
          showPopConfirm.value = true;
          return;
        }
        createAccountRuleRun(params);
      }).finally(() => {
        isSubmitting.value = false;
      });
  };
</script>

<style lang="less" scoped>
  .rule-form {
    padding: 24px 40px 32px;

    .rule-setting-box {
      padding: 16px 0 16px 16px;
      background: #f5f7fa;
      border-radius: 2px;
    }

    .form-item {
      :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;
      }
    }

    .rule-form-row {
      display: flex;
      width: 100%;
      align-items: flex-start;

      .checkbox-group {
        display: flex;
        flex: 1;
        flex-wrap: wrap;

        .bk-checkbox {
          min-width: 33.33%;
          margin-bottom: 16px;
          margin-left: 0;

          .sensitive-tip {
            height: 16px;
            padding: 0 4px;
            font-size: 10px;
            line-height: 16px;
            color: #fe9c00;
            text-align: center;
            background: #fff3e1;
            border-radius: 2px;
          }
        }
      }

      .check-all {
        position: relative;
        width: 48px;
        margin-right: 48px;

        :deep(.bk-checkbox-label) {
          word-break: keep-all;
        }
      }

      .check-all::after {
        position: absolute;
        top: 50%;
        right: -24px;
        width: 1px;
        height: 14px;
        background-color: #c4c6cc;
        content: '';
        transform: translateY(-50%);
      }
    }

    :deep(.privilege .bk-form-label::after) {
      position: absolute;
      top: 0;
      width: 14px;
      color: @danger-color;
      text-align: center;
      content: '*';
    }

    :deep(.privilege .is-required .bk-form-label::after) {
      display: none;
    }
  }
</style>
<style lang="less">
  .pre-check-content {
    width: 100%;
    max-height: 500px;
    overflow-y: auto;
  }
</style>
