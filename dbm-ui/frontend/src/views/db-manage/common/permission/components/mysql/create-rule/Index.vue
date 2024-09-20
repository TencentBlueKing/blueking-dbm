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
    class="create-rule-sideslider"
    :is-show="isShow"
    render-directive="if"
    :title="isEdit ? t('编辑授权规则') : t('添加授权规则')"
    :width="840"
    @closed="() => handleClose(true)">
    <RuleSettings
      v-if="isFirstStep"
      ref="ruleSettingsRef"
      :account-type="accountType"
      :is-edit="isEdit"
      :rule-settings-config="configMap[accountType]"
      :rules-form-data="rulesFormData" />
    <PreviewDiff
      v-else
      ref="previewDiffRef"
      :rule-settings-config="configMap[accountType]"
      :rules-form-data="rulesFormData" />
    <template #footer>
      <BkButton
        v-if="!isFirstStep"
        class="w-88"
        @click="() => (currentStep = 1)">
        {{ t('上一步') }}
      </BkButton>
      <BkButton
        v-if="isFirstStep && isEdit"
        class="w-88 mr-8"
        theme="primary"
        @click="handleGoPreviewDiff">
        {{ t('差异确认') }}
      </BkButton>
      <BkPopConfirm
        v-else
        :content="precheckWarnTip"
        :is-show="showPopConfirm"
        :title="t('确定提交？')"
        trigger="manual"
        width="400"
        @cancel="handleVerifyCancel"
        @confirm="handleVerifyConfirm">
        <BkButton
          class="w-88 mr-8 ml-8"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
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

  import { createAccountRule, modifyAccountRule, preCheckAddAccountRule } from '@services/source/mysqlPermissionAccount';
  import { createTicket } from '@services/source/ticket';
  import type { AccountRule, AccountRulePrivilege, PermissionRuleInfo } from '@services/types/permission';

  import { useBeforeClose,useTicketMessage } from '@hooks';

  import { AccountTypes, TicketTypes } from '@common/const';

  import { messageError, messageSuccess } from '@utils';

  import configMap from '../config';

  import PreviewDiff from './components/PreviewDiff.vue';
  import RuleSettings from './components/RuleSettings.vue';

  interface Props {
    accountId?: number;
    ruleObj?: PermissionRuleInfo;
    accountType?: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountId: -1,
    ruleObj: undefined,
    accountType: AccountTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const handleBeforeClose = useBeforeClose();

  const initFormData = (): AccountRule => ({
    account_id: null,
    access_db: '',
    privilege: {
      ddl: [],
      dml: [],
      glob: [],
    },
  });

  const ruleSettingsRef = ref<InstanceType<typeof RuleSettings>>();
  const previewDiffRef = ref<InstanceType<typeof PreviewDiff>>();
  const currentStep = ref(1);
  const showPopConfirm = ref(false);
  const precheckWarnTip = ref<JSX.Element>();
  const isSubmitting = ref(false);
  const rulesFormData = reactive<{
    beforeChange: AccountRule;
    afterChange: AccountRule;
  }>({
    beforeChange: initFormData(),
    afterChange: initFormData(),
  });
  let userName = ''

  const isEdit = computed(() => !!props.ruleObj?.account_id);
  const isFirstStep = computed(() => currentStep.value === 1);

  /**
   * 添加授权规则
   */
  const { run: createAccountRuleRun } = useRequest(createAccountRule, {
    manual: true,
    onSuccess() {
      messageSuccess(t('成功添加授权规则'));
      emits('success');
    },
    onError() {
      messageError(t('提交失败'));
    },
    onAfter() {
      isSubmitting.value = false;
      handleClose();
    }
  })

  /**
   * 编辑授权规则
   */
  const { run: modifyAccountRuleRun } = useRequest(modifyAccountRule, {
    manual: true,
    onSuccess() {
      messageSuccess(t('编辑授权规则成功'));
      emits('success');
    },
    onError() {
      messageError(t('提交失败'));
    },
    onAfter() {
      isSubmitting.value = false;
      handleClose();
    }
  })

  /**
   * 规则变更（有权限被删除）时走单据
   */
  const { run: createTicketRun } = useRequest(createTicket, {
    manual: true,
    onSuccess(data) {
      window.changeConfirm = false;
      handleClose();
      ticketMessage(data.id);
      emits('success');
    },
    onAfter() {
      isSubmitting.value = false;
    }
  })

  watch(
    isShow,
    () => {
      rulesFormData.beforeChange = {
        account_id: props.accountId ?? -1,
        access_db: props.ruleObj?.access_db || '',
        privilege: props.ruleObj?.privilege ? Object.entries(configMap[props.accountType].dbOperations).reduce<AccountRulePrivilege>((acc, [key, values]) => {
          acc[key as keyof AccountRulePrivilege] = values.filter(value => props.ruleObj?.privilege.includes(value));
          return acc
        }, {} as AccountRulePrivilege) : {},
      } as AccountRule;
    },
    {
      immediate: true,
    },
  );

  const handleClose = async (isNeedCloseConfirm = false) => {
    if (isNeedCloseConfirm) {
      const result = await handleBeforeClose();
      if (!result) {
        return;
      }
    }
    isShow.value = false;
    window.changeConfirm = false;
    rulesFormData.beforeChange = initFormData();
    rulesFormData.afterChange = initFormData();
    currentStep.value = 1;
  };

  const handleVerifyCancel = () => {
    showPopConfirm.value = false;
    isSubmitting.value = false;
  };

  const generateRequestParam = async () => {
    let accountRule: AccountRule;
    if (isFirstStep.value) {
      const ruleSettingResult = await ruleSettingsRef.value!.getValue();
      accountRule = ruleSettingResult.accountRule;
      userName = ruleSettingResult.userName;
    } else {
      accountRule = _.cloneDeep(rulesFormData.afterChange);
    }
    return {
      ...accountRule,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      access_db: accountRule.access_db.replace(/\n|;/g, ','), // 统一分隔符
      account_type: props.accountType,
    };
  };

  const handleVerifyConfirm = async () => {
    showPopConfirm.value = false;
    const params = await generateRequestParam();
    createAccountRuleRun(params);
  };

  const handleGoPreviewDiff = async () => {
    const ruleSettingResult = await ruleSettingsRef.value!.getValue();
    rulesFormData.afterChange = ruleSettingResult.accountRule;
    userName = ruleSettingResult.userName;
    currentStep.value = 2;
  };

  const handleSubmit = async () => {
    isSubmitting.value = true;
    const params = await generateRequestParam();
    if (isEdit.value && previewDiffRef.value) {
      const { changed } = previewDiffRef.value;
      const isAccessDbChanged = changed.accessDb;
      const isHasDelete = changed.privilege.deleteCount > 0;
      if (isAccessDbChanged || isHasDelete) {
        const ticketTypeMap = {
          [AccountTypes.MYSQL]: TicketTypes.MYSQL_ACCOUNT_RULE_CHANGE,
          [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_ACCOUNT_RULE_CHANGE,
        }
        createTicketRun({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          ticket_type: ticketTypeMap[props.accountType],
          remark: '',
          details: {
            last_account_rules: {
              userName,
              ...rulesFormData.beforeChange
            },
            action: 'change',
            ...params,
            rule_id: props.ruleObj!.rule_id,
          },
        });
      } else {
        modifyAccountRuleRun({
          ...params,
          rule_id: props.ruleObj!.rule_id,
        });
      }
    } else {
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
        })
        .finally(() => {
          isSubmitting.value = false;
        });
    }
  };
</script>

<style lang="less">
  .create-rule-sideslider {
    position: relative;

    .bk-modal-footer {
      position: absolute;
      bottom: 0;
      width: 100%;

      .bk-sideslider-footer {
        margin: 24px 0;
      }
    }
  }
</style>
