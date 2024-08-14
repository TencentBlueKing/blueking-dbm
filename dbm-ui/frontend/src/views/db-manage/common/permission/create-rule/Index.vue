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
    render-directive="if"
    :title="isEdit ? t('编辑授权规则') : t('添加授权规则')"
    :width="840"
    @closed="() => handleClose(true)">
    <RuleSettings
      v-if="isFirstStep"
      ref="ruleSettingsRef"
      :is-edit="isEdit"
      :rule-settings-config="ruleSettingsConfig"
      :rules-form-data="rulesFormData" />
    <PreviewDiff
      v-else
      :rule-settings-config="ruleSettingsConfig"
      :rules-form-data="rulesFormData" />
    <template #footer>
      <BkButton
        v-if="!isFirstStep"
        class="w-88"
        @click="() => (currentStep = 1)">
        {{ t('上一步') }}
      </BkButton>
      <BkButton
        v-if="isFirstStep"
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

  import MysqlPermissonAccountModel from '@services/model/mysql-permisson/mysql-permission-account';
  import { createAccountRule, modifyAccountRule, preCheckAddAccountRule } from '@services/source/permission';
  import type { AccountRule, AccountRulePrivilege } from '@services/types/permission';

  import { useBeforeClose } from '@hooks';

  import { AccountTypes, DBTypes } from '@common/const';

  import { messageError, messageSuccess } from '@utils';

  import PreviewDiff from './components/PreviewDiff.vue';
  import RuleSettings from './components/RuleSettings.vue';

  export interface RuleSettingsConfig {
    accountType: AccountTypes;
    dbOperations: {
      ddl: string[];
      dml: string[];
      glob: string[];
    };
    ddlSensitiveWords?: string[];
  }

  export type AuthItemKey = keyof RuleSettingsConfig['dbOperations'];

  export interface RulesFormData {
    beforeChange: AccountRule;
    afterChange: AccountRule;
  }

  interface Props {
    accountId?: number;
    ruleObj?: MysqlPermissonAccountModel['rules'][number];
    dbType?: DBTypes;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountId: -1,
    ruleObj: undefined,
    dbType: DBTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
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
  const currentStep = ref(1);
  const showPopConfirm = ref(false);
  const precheckWarnTip = ref<JSX.Element>();
  const isSubmitting = ref(false);
  const rulesFormData = reactive<RulesFormData>({
    beforeChange: initFormData(),
    afterChange: initFormData(),
  });

  const configMap: { [key in DBTypes]?: RuleSettingsConfig } = {
    [DBTypes.MYSQL]: {
      accountType: AccountTypes.MYSQL,
      dbOperations: {
        dml: ['select', 'insert', 'update', 'delete', 'show view'],
        ddl: [
          'create',
          'alter',
          'drop',
          'index',
          'create view',
          'execute',
          'trigger',
          'event',
          'create routine',
          'alter routine',
          'references',
          'create temporary tables',
        ],
        glob: ['file', 'reload', 'show databases', 'process', 'replication slave', 'replication client'],
      },
      ddlSensitiveWords: [
        'trigger',
        'event',
        'create routine',
        'alter routine',
        'references',
        'create temporary tables',
      ],
    },
    [DBTypes.TENDBCLUSTER]: {
      accountType: AccountTypes.TENDBCLUSTER,
      dbOperations: {
        dml: ['select', 'insert', 'update', 'delete'],
        ddl: ['execute'],
        glob: ['file', 'reload', 'process', 'show databases'],
      },
    },
  };

  const isEdit = computed(() => !!props.ruleObj?.account_id);
  const isFirstStep = computed(() => currentStep.value === 1);
  const ruleSettingsConfig = computed(() => {
    const { accountType, dbOperations, ddlSensitiveWords } = configMap[props.dbType as DBTypes] as RuleSettingsConfig;
    return {
      accountType,
      dbOperations,
      ddlSensitiveWords: ddlSensitiveWords || [],
    };
  });

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
   * 创建时检验是否已存在规则
   */
  const { run: preCheckAddAccountRuleRun } = useRequest(preCheckAddAccountRule, {
    manual: true,
    onSuccess({ warning }) {
      if (warning) {
        precheckWarnTip.value = (
          <div class="pre-check-content">
            {warning.split('\n').map(line => <div>{line}</div>)}
          </div>
        );
        showPopConfirm.value = true;
        return;
      }
      const params = generateRequestParam();
      createAccountRuleRun(params);
    },
    onError() {
      messageError(t('提交失败'));
    },
    onAfter() {
      isSubmitting.value = false;
      handleClose();
    }
  })

  watch(
    isShow,
    () => {
      rulesFormData.beforeChange = {
        ...initFormData(),
        account_id: props.accountId ?? -1,
        access_db: props.ruleObj?.access_db || '',
        privilege: props.ruleObj?.privilege ? Object.entries(ruleSettingsConfig.value.dbOperations).reduce<AccountRulePrivilege>((acc, [key, values]) => {
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

  const generateRequestParam = () => {
    const formData = _.cloneDeep(rulesFormData.afterChange);
    return {
      ...formData,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      access_db: formData.access_db.replace(/\n|;/g, ','), // 统一分隔符
      account_type: ruleSettingsConfig.value.accountType,
    };
  };

  const handleVerifyConfirm = () => {
    showPopConfirm.value = false;
    const params = generateRequestParam();
    createAccountRuleRun(params);
  };

  const handleGoPreviewDiff = async () => {
    const validResult = await ruleSettingsRef.value!.validate();
    rulesFormData.afterChange = validResult;
    currentStep.value = 2;
  };

  const handleSubmit = async () => {
    isSubmitting.value = true;
    const params = generateRequestParam();
    if (isEdit.value) {
      modifyAccountRuleRun({
        ...params,
        rule_id: props.ruleObj!.rule_id,
      })
    } else {
      preCheckAddAccountRuleRun(params)
    }
  };
</script>
