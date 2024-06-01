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
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :title="t('添加授权规则')"
    :width="840"
    @closed="handleClose">
    <DbForm
      ref="ruleRef"
      class="rule-form"
      form-type="vertical"
      :model="state.formdata"
      :rules="rules">
      <BkFormItem
        :label="t('账号名')"
        property="account_id"
        required>
        <BkSelect
          v-model="state.formdata.account_id"
          :clearable="false"
          filterable
          :input-search="false"
          :loading="state.isLoading">
          <BkOption
            v-for="item of state.accounts"
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
        <DbTextarea
          ref="textareaRef"
          v-model="state.formdata.access_db"
          :max-height="400"
          :placeholder="t('请输入DB名称_可以使用通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔')"
          :teleport-to-body="false" />
      </BkFormItem>
      <BkFormItem
        class="rule-form__item"
        :label="t('权限设置')"
        property="auth">
        <div class="rule-setting-box">
          <BkFormItem label="DML">
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
                v-model="state.formdata.privilege.dml"
                class="rule-form-checkbox-group">
                <BkCheckbox
                  v-for="dmlItem of dbOperations.dml"
                  :key="dmlItem"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges"
                  :label="dmlItem">
                  {{ dmlItem }}
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
          <BkFormItem label="DDL">
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
                v-model="state.formdata.privilege.ddl"
                class="rule-form-checkbox-group">
                <BkCheckbox
                  v-for="ddlItem of dbOperations.ddl"
                  :key="ddlItem"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges"
                  :label="ddlItem">
                  {{ ddlItem }}
                  <span
                    v-if="ddlSensitiveWords.includes(ddlItem)"
                    class="sensitive-tip">
                    {{ t('敏感') }}
                  </span>
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
          <BkFormItem
            class="mb-0"
            :label="t('全局')">
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
                v-model="state.formdata.privilege.glob"
                class="rule-form-checkbox-group">
                <BkCheckbox
                  v-for="globItem of dbOperations.glob"
                  :key="globItem"
                  v-bk-tooltips="{
                    content: t('你已选择所有权限'),
                    disabled: !checkAllPrivileges,
                  }"
                  :disabled="checkAllPrivileges"
                  :label="globItem">
                  {{ globItem }}
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
          class="mr-8"
          :loading="state.isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton
        :disabled="state.isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import type { JSX } from 'vue/jsx-runtime';
  import { useI18n } from 'vue-i18n';

  import { createAccountRule, getPermissionRules, preCheckAddAccountRule, queryAccountRules } from '@services/permission';
  import type { AccountRule, PermissionRuleAccount } from '@services/types/permission';

  import { useStickyFooter  } from '@hooks';

  import { AccountTypes } from '@common/const';

  import { dbOperations, ddlSensitiveWords } from '../common/const';

  type AuthItemKey = keyof typeof dbOperations;

  interface Props {
    accountId?: number
  }

  interface Emits {
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    accountId: -1,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const initFormdata = (): AccountRule => ({
    account_id: null,
    access_db: '',
    privilege: {
      ddl: [],
      dml: [],
      glob: [],
    },
  });

  const getTextareaHeight = () => {
    textareaHeight.value = 0;

    if (textareaRef.value) {
      const el = textareaRef.value.$el as HTMLDivElement;
      textareaHeight.value = el.firstElementChild?.scrollHeight ?? 0;
    }
  };

  const { t } = useI18n();

  const ruleRef = ref();
  const checkAllPrivileges = ref(false);
  const showPopConfirm = ref(false);
  const precheckWarnTip = ref<JSX.Element>();
  const textareaRef = ref();
  const textareaHeight = ref(0);

  const state = reactive({
    formdata: initFormdata(),
    accounts: [] as PermissionRuleAccount[],
    isLoading: false,
    isSubmitting: false,
    existDBs: [] as string[],
  });

  const selectedUserInfo = computed(() => state.accounts.find(item => item.account_id === state.formdata.account_id));

  const rules = computed(() => ({
    auth: [
      {
        trigger: 'change',
        message: t('请设置权限'),
        validator: () => {
          const { ddl, dml, glob } = state.formdata.privilege;
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
        message: () => t('该账号下已存在xx规则', [state.existDBs.join('，')]),
        validator: verifyAccountRules,
      },
    ],
  }));

  watch(isShow, (show) => {
    if (show) {
      state.formdata.account_id = props.accountId ?? -1;
      getAccount();
    }
  });

  watch(() => state.formdata.access_db, getTextareaHeight);

  /** 设置底部按钮粘性布局 */
  useStickyFooter(ruleRef);

  // const handleSelectAllPrivileges = (checked: boolean) => {
  //   checkAllPrivileges.value = checked;
  //   if (checked) {
  //     state.formdata.privilege.ddl = [];
  //     state.formdata.privilege.dml = [];
  //     state.formdata.privilege.glob = [];
  //   }
  // };

  // 获取权限设置全选框状态
  const getAllCheckedboxValue = (key: AuthItemKey) => state.formdata.privilege[key].length === dbOperations[key].length;
  const getAllCheckedboxIndeterminate = (key: AuthItemKey) => (
    state.formdata.privilege[key].length > 0
    && state.formdata.privilege[key].length !== dbOperations[key].length
  );
  const handleSelectedAll = (key: AuthItemKey, value: boolean) => {
    if (value) {
      state.formdata.privilege[key] = [...dbOperations[key]];
      return;
    }

    state.formdata.privilege[key] = [];
  };

  const verifyAccountRules = () => {
    const user = selectedUserInfo.value?.user;
    const dbs = state.formdata.access_db.replace(/\n|;/g, ',')
      .split(',')
      .filter(db => db);

    if (!user || dbs.length === 0) return false;

    return queryAccountRules({
      bizId: window.PROJECT_CONFIG.BIZ_ID,
      user,
      access_dbs: dbs,
      account_type: 'mysql',
    })
      .then((res) => {
        const rules = res.results[0]?.rules || [];
        state.existDBs = rules.map(item => item.access_db);
        return rules.length === 0;
      });
  };

  /**
   * 获取账号列表
   */
  const getAccount = () => {
    state.isLoading = true;
    getPermissionRules({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      account_type: 'mysql',
    })
      .then((res) => {
        state.accounts = res.results.map(item => item.account);
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  const handleBeforeClose = () => {
    if (window.changeConfirm) {
      return new Promise((resolve) => {
        InfoBox({
          title: t('确认离开当前页'),
          content: t('离开将会导致未保存信息丢失'),
          confirmText: t('离开'),
          cancelText: t('取消'),
          onConfirm: () => {
            window.changeConfirm = false;
            resolve(true);
            return true;
          },
        });
      });
    }
    return true;
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();
    if (!result) return;
    isShow.value = false;
    state.formdata = initFormdata();
    // checkAllPrivileges.value = false;
    state.existDBs = [];
    window.changeConfirm = false;
  };

  const handleVerifyCancel = () => {
    showPopConfirm.value = false;
    state.isSubmitting = false;
  };

  const submitCreateAccountRule = (params: ServiceParameters<typeof createAccountRule>) => {
    createAccountRule(params)
      .then(() => {
        Message({
          message: t('成功添加授权规则'),
          theme: 'success',
        });
        emits('success');
        window.changeConfirm = false;
        handleClose();
      })
      .finally(() => {
        state.isSubmitting = false;
      });
  };

  const generateRequestParam = () => {
    const formData = _.cloneDeep(state.formdata);
    if (checkAllPrivileges.value) {
      // 包含所有权限
      formData.privilege.glob = ['all privileges'];
    }

    return ({
      ...formData,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      access_db: formData.access_db.replace(/\n|;/g, ','), // 统一分隔符
      account_type: AccountTypes.MYSQL,
    });
  };

  const handleVerifyConfirm = () => {
    showPopConfirm.value = false;
    const params = generateRequestParam();
    submitCreateAccountRule(params);
  };


  const handleSubmit = async () => {
    await ruleRef.value.validate();
    state.isSubmitting = true;
    const params = generateRequestParam();
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
        submitCreateAccountRule(params);
      });
  };
</script>

<style lang="less" scoped>
  .rule-form {
    padding: 24px 40px 40px;

    .rule-setting-box {
      padding: 16px 0 16px 16px;
      background: #f5f7fa;
      border-radius: 2px;
    }

    &__textarea {
      height: var(--height);
      max-height: 160px;
      min-height: 32px;

      :deep(textarea) {
        line-height: 1.8;
      }
    }

    &__item {
      :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;

        &::after {
          position: absolute;
          top: 0;
          width: 14px;
          line-height: 24px;
          color: @danger-color;
          text-align: center;
          content: '*';
        }
      }
    }

    .rule-form-row {
      display: flex;
      width: 100%;
      align-items: flex-start;

      .rule-form-checkbox-group {
        display: flex;
        flex: 1;
        flex-wrap: wrap;

        .bk-checkbox {
          min-width: 33.33%;
          margin-bottom: 16px;
          margin-left: 0;

          .sensitive-tip {
            background: #fff3e1;
            border-radius: 2px;
            font-size: 10px;
            color: #fe9c00;
            height: 16px;
            line-height: 16px;
            text-align: center;
            padding: 0 4px;
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

        &::after {
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
