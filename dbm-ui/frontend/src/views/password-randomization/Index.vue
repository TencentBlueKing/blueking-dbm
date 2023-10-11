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
  <div />
  <!-- <BkLoading :loading="loading">
    <DbForm
      ref="formRef"
      class="password-randomization"
      :label-width="260"
      :model="formData">
      <BkFormItem
        :label="t('MySQL 管理账号')">
        <span>{{ passwordVisible ? formData.password : unVisiblePassword }}</span>
        <DbIcon
          class="password-icon"
          type="visible1"
          @click="passwordVisible = !passwordVisible" />
      </BkFormItem>
      <BkFormItem
        class="form-item-group"
        :label="t('于')"
        property="timeData"
        required
        :rules="timeDataRules">
        <BkSelect
          v-model="formData.timeData.typeValue"
          :clearable="false">
          <BkOption
            v-for="(item, index) in typeOptions"
            :key="index"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
        <BkSelect
          v-if="typeValue === 'week'"
          v-model="formData.timeData.weekValue"
          class="group-item"
          :clearable="false"
          multiple>
          <BkOption
            v-for="(item, index) in weekOptions"
            :key="index"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
        <BkSelect
          v-if="typeValue === 'month'"
          v-model="formData.timeData.monthValue"
          class="group-item date-selector"
          :clearable="false"
          multiple
          :popover-options="{
            extCls: 'password-randomization-date-selector-popover'
          }">
          <BkOption
            v-for="(item, index) in monthOptions"
            :key="index"
            :label="item.label"
            :value="item.value">
            {{ item.value }}
          </BkOption>
        </BkSelect>
        <BkTimePicker
          v-model="formData.timeData.timeValue"
          append-to-body
          class="group-item datavalue-selector"
          :clearable="false"
          :editable="false"
          format="HH:mm"
          :show-date="false"
          type="time" />
        <span class="ml-8">{{ t('随机化一次密码') }}</span>
      </BkFormItem>
      <BkFormItem :label="t('密码复杂度')">
        <div class="complexity-box">
          <div class="complexity-head">
            {{ t('密码规则') }}
          </div>
          <div class="complexity-content">
            <div class="complexity-item">
              {{ t('长度') }}：
              <span class="complexity-item-value">
                {{ passwordPolicyData?.rule.min_length }} ~ {{ passwordPolicyData?.rule.max_length }} {{ t('位') }}
              </span>
            </div>
            <div class="complexity-item">
              {{ t('密码必须包含') }}：
              <span class="complexity-item-value">
                {{ complexity.includeRules }}
              </span>
            </div>
            <div class="complexity-item">
              {{ t('密码不允许连续n位出现', [passwordPolicyData?.rule.exclude_continuous_rule.limit]) }}：
              <span class="complexity-item-value">
                {{ complexity.excludeContinuousRules }}
              </span>
            </div>
          </div>
        </div>
      </BkFormItem>
    </DbForm>
    <div class="password-randomization-footer">
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleSubmit()">
        {{ t('保存') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会恢复默认设置的内容！')"
        :title="t('确认重置当前配置？')">
        <BkButton>
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </div>
  </BkLoading> -->
</template>

<script setup lang="ts">
  // import { Message } from 'bkui-vue';
  // import { useI18n } from 'vue-i18n';
  // import { useRequest } from 'vue-request';

  // import {
  //   getPasswordPolicy,
  //   modifyRandomCycle,
  //   queryRandomCycle,
  // } from '@services/permission';

  // const initData = () => ({
  //   typeValue: 'day',
  //   weekValue: [] as string[],
  //   monthValue: [] as string[],
  //   timeValue: '00:00',
  // });

  // type PasswordPolicyRule = ServiceReturnType<typeof getPasswordPolicy>['rule']

  // const { t } = useI18n();

  // let submitType: 'edit' | 'reset' = 'edit';

  // const timeDataRules = [
  //   {
  //     required: true,
  //     message: t('请选择'),
  //     validator() {
  //       const {
  //         typeValue,
  //         weekValue,
  //         monthValue,
  //         timeValue,
  //       } = formData.timeData;

  //       if (typeValue === 'day') {
  //         return timeValue !== '';
  //       }
  //       if (typeValue === 'week') {
  //         return weekValue.length > 0 && timeValue !== '';
  //       }
  //       if (typeValue === 'month') {
  //         return monthValue.length > 0 && timeValue !== '';
  //       }

  //       return true;
  //     },
  //   },
  // ];

  // const POLICY_MAP: {
  //   includeRule: Record<string, string>
  //   excludeContinuousRule: Record<string, string>
  // } = {
  //   includeRule: {
  //     uppercase: t('大写字母'),
  //     lowercase: t('小写字母'),
  //     numbers: t('数字'),
  //     symbols: t('特殊字符_除空格外'),
  //   },
  //   excludeContinuousRule: {
  //     keyboards: t('键盘序'),
  //     letters: t('字母序'),
  //     numbers: t('数字序'),
  //     repeats: t('连续特殊符号序'),
  //     symbols: t('重复字母_数字_特殊符号'),
  //   },
  // };

  // const monthOptions = new Array(31).fill('')
  //   .map((_, index) => ({
  //     label: `${index + 1}${t('号')}`,
  //     value: `${index + 1}`,
  //   }));

  // const formRef = ref();
  // const passwordVisible = ref(false);
  // const typeOptions = ref([
  //   {
  //     value: 'day',
  //     label: t('每天'),
  //   },
  //   {
  //     value: 'week',
  //     label: t('每周'),
  //   },
  //   {
  //     value: 'month',
  //     label: t('每月'),
  //   },
  // ]);

  // const weekOptions = ref([
  //   {
  //     value: '1',
  //     label: t('周一'),
  //   },
  //   {
  //     value: '2',
  //     label: t('周二'),
  //   },
  //   {
  //     value: '3',
  //     label: t('周三'),
  //   },
  //   {
  //     value: '4',
  //     label: t('周四'),
  //   },
  //   {
  //     value: '5',
  //     label: t('周五'),
  //   },
  //   {
  //     value: '6',
  //     label: t('周六'),
  //   },
  //   {
  //     value: '7',
  //     label: t('周日'),
  //   },
  // ]);

  // const formData = reactive({
  //   password: 'ADMIN',
  //   timeData: initData(),
  // });

  // const complexity = reactive({} as {
  //   includeRules: string,
  //   excludeContinuousRules: string
  // });

  // const unVisiblePassword = computed(() => '*'.repeat(formData.password.length));
  // const typeValue = computed(() => formData.timeData.typeValue);

  // const { data: passwordPolicyData } = useRequest(getPasswordPolicy, {
  //   onSuccess(passwordPolicy) {
  //     const { rule } = passwordPolicy;
  //     const {
  //       includeRule,
  //       excludeContinuousRule,
  //     } = POLICY_MAP;

  //     const includeRules = Object.keys(includeRule).reduce((includeRulePrev, includeRuleKey) => {
  //       if (rule.include_rule[includeRuleKey as keyof PasswordPolicyRule['include_rule']]) {
  //         return [...includeRulePrev, includeRule[includeRuleKey]];
  //       }

  //       return includeRulePrev;
  //     }, [] as string[]);

  //     const excludeContinuousRules = Object.keys(excludeContinuousRule)
  //       .reduce((excludeContinuousRulePrev, excludeContinuousRuleKey) => {
  // eslint-disable-next-line max-len
  //         if (rule.exclude_continuous_rule[excludeContinuousRuleKey as keyof PasswordPolicyRule['exclude_continuous_rule']]) {
  //           return [...excludeContinuousRulePrev, excludeContinuousRule[excludeContinuousRuleKey]];
  //         }

  //         return excludeContinuousRulePrev;
  //       }, [] as string[]);

  //     complexity.includeRules = includeRules.join('、');
  //     complexity.excludeContinuousRules = excludeContinuousRules.join('、');
  //   },
  // });

  // useRequest(queryRandomCycle, {
  //   onSuccess(randomCycle) {
  //     const {
  //       minute,
  //       hour,
  //       day_of_week: dayOfWeek,
  //       day_of_month: dayOfMonth,
  //     } = randomCycle.crontab;
  //     const formDataRes = initData();

  //     formDataRes.timeValue = `${hour}:${minute}`;

  //     if (dayOfWeek !== '*') {
  //       formDataRes.weekValue = dayOfWeek.split(',');
  //       formDataRes.typeValue = 'week';
  //     } else if (dayOfMonth !== '*') {
  //       formDataRes.monthValue = dayOfMonth.split(',');
  //       formDataRes.typeValue = 'month';
  //     }

  //     Object.assign(formData.timeData, formDataRes);
  //   },
  // });

  // const {
  //   run: modifyRandomCycleRun,
  //   loading,
  // } = useRequest(modifyRandomCycle, {
  //   manual: true,
  //   onSuccess() {
  //     if (submitType === 'reset') {
  //       Object.assign(formData.timeData, initData());
  //     }
  //     window.changeConfirm = false;
  //     Message({
  //       theme: 'success',
  //       message: submitType === 'edit' ? t('保存成功') : t('重置成功'),
  //     });
  //   },
  // });

  // const handleReset = () => {
  //   submitType = 'reset';
  //   modifyRandomCycleRun({
  //     crontab: {
  //       hour: '0',
  //       minute: '0',
  //       day_of_week: '*',
  //       day_of_month: '*',
  //     },
  //   });
  // };

  // const handleSubmit = async () => {
  //   await formRef.value.validate();

  //   const {
  //     typeValue,
  //     weekValue,
  //     monthValue,
  //     timeValue,
  //   } = formData.timeData;
  //   const [hour, minute] = timeValue.split(':');
  //   const params: ServiceReturnType<typeof queryRandomCycle> = {
  //     crontab: {
  //       hour,
  //       minute,
  //       day_of_week: '*',
  //       day_of_month: '*',
  //     },
  //   };

  //   if (typeValue === 'week') {
  //     params.crontab.day_of_week = weekValue.join(',');
  //   } else if (typeValue === 'month') {
  //     params.crontab.day_of_month = monthValue.join(',');
  //   }

  //   submitType = 'edit';
  //   modifyRandomCycleRun(params);
  // };
</script>

<style lang="less" scoped>
  .password-randomization {
    padding: 32px 0;
    font-size: @font-size-mini;
    background-color: #FFF;

    .password-icon {
      margin-left: 4px;
      font-size: 16px;
      cursor: pointer;
    }

    .form-item-group {
      margin-bottom: 32px;

      :deep(.bk-form-content) {
        display: flex;
      }

      :deep(.bk-form-error) {
        top: 36px;
        padding-top: 0;
      }

      .group-item {
        margin-left: 4px;
      }
    }

    .date-selector {
      width: 260px;
    }

    .datavalue-selector {
      width: 150px;
    }

    .complexity-box {
      display: inline-block;
      border: 1px solid #DCDEE5;
      border-radius: 2px;

      .complexity-head {
        padding-left: 16px;
        font-weight: 700;
        color: #63656E;
        background-color: #FAFBFD;
        border-bottom: 1px solid #DCDEE5;
      }

      .complexity-content {
        padding: 12px 16px 12px 32px;

        .complexity-item {
          position: relative;
          height: 32px;
          line-height: 32px;

          &::before {
            position: absolute;
            top: 14px;
            left: -13px;
            display: block;
            width: 4px;
            height: 4px;
            background: #979BA5;
            border-radius: 50%;
            content: '';
          }

          .complexity-item-value {
            color: #313238;
          }
        }
      }
    }
  }

  .password-randomization-footer {
    margin: 32px 0 0 260px;

    .bk-button {
      width: 88px;
    }
  }
</style>

<style lang="less">
  .password-randomization-date-selector-popover {
    .bk-select-options {
      display: flex;
      flex-wrap: wrap;
      padding: 4px 12px !important;
    }

    .bk-select-option {
      justify-content: center;
      width: calc(100% / 7);
      padding: 0 !important;
    }

    .bk-select-selected-icon {
      display: none !important;
    }
  }
</style>
