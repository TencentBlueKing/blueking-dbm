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
  <BkLoading :loading="isLoading">
    <DbForm
      ref="formRef"
      class="password-policy"
      :label-width="260"
      :model="formData"
      :rules="rules">
      <DbCard
        mode="collapse"
        :title="t('密码组成设置')">
        <BkFormItem
          :label="t('密码长度')"
          required>
          <BkInput
            v-model="formData.min_length"
            class="password-policy-number mr-6"
            :max="defaultConfig.max_length"
            :min="defaultConfig.min_length"
            type="number" />
          <span class="password-policy-text">{{ t('至') }}</span>
          <BkInput
            v-model="formData.max_length"
            class="password-policy-number ml-6"
            :max="defaultConfig.max_length"
            :min="defaultConfig.min_length"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="t('密码组成')"
          property="include_rule"
          required>
          <BkCheckbox
            v-model="formData.include_rule.lowercase"
            :false-label="false"
            @change="handleChangeIncludeRule">
            {{ t('小写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.include_rule.uppercase"
            :false-label="false"
            @change="handleChangeIncludeRule">
            {{ t('大写字母') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.include_rule.numbers"
            :false-label="false"
            @change="handleChangeIncludeRule">
            {{ t('数字') }}
          </BkCheckbox>
          <BkCheckbox
            v-model="formData.include_rule.symbols"
            :false-label="false"
            @change="handleChangeIncludeRule">
            {{ t('特殊字符（非空格）') }}
          </BkCheckbox>
          <div
            v-if="formData.include_rule.symbols"
            class="password-policy-input-box">
            <div class="input-prefix">
              {{ t('指定特殊字符') }}
            </div>
            <BkFormItem
              class="symbols-input"
              property="symbols_allowed">
              <BkInput
                v-model="formData.symbols_allowed"
                :placeholder="t('请输入英文半角字符，重复字符将去重')" />
            </BkFormItem>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('密码校验')"
          property="number_of_types"
          required>
          {{ t('包含上述任意') }}
          <BkInput
            v-model="formData.number_of_types"
            class="password-policy-number ml-6 mr-6"
            :max="typeMaxCount"
            :min="1"
            type="number" />
          {{ t('种类型') }}
        </BkFormItem>
        <BkFormItem
          :label="t('开启弱密码检测')"
          required>
          <div class="password-policy-weak mb-16">
            <BkSwitcher
              v-model="formData.weak_password"
              theme="primary" />
            <span class="ml-10">
              {{ t('开启后，不允许超过 x 位连续字符，如出现以下示例密码将无法通过检测', { x: defaultConfig.repeats }) }}
            </span>
          </div>
          <ul class="password-policy-rules">
            <li>{{ t('连续键盘序_如_xx', excludeContinuousRule.keyboards) }}</li>
            <li>{{ t('连续字母序_如_xx', excludeContinuousRule.letters) }}</li>
            <li>{{ t('连续数字序_如_xx', excludeContinuousRule.numbers) }}</li>
            <li>{{ t('连续特殊符号序_如_xx', excludeContinuousRule.symbols) }}</li>
            <li>{{ t('重复的字母_数字_特殊符号_如_aa_bb_cc', excludeContinuousRule.repeats) }}</li>
          </ul>
        </BkFormItem>
      </DbCard>
      <BkFormItem class="password-policy-footer">
        <AuthButton
          action-id="password_policy_set"
          class="mr-8"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit()">
          {{ t('保存') }}
        </AuthButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会恢复默认设置的内容')"
          :title="t('确认重置')">
          <BkButton :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </BkFormItem>
    </DbForm>
  </BkLoading>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getPasswordPolicy, updatePasswordPolicy } from '@services/source/permission';

  import { DBTypes } from '@common/const';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const initData = () => ({
    repeats: 0,
    max_length: 32,
    min_length: 8,
    include_rule: {
      numbers: true,
      symbols: true,
      lowercase: true,
      uppercase: true,
    },
    weak_password: false,
    number_of_types: 0,
    symbols_allowed: '',
  });

  const { t } = useI18n();

  const passwordPolicyData = {
    id: 0,
    name: '',
  };

  const rules = {
    include_rule: [
      {
        trigger: 'change',
        message: t('请至少选择一种类型'),
        validator: () => Object.values(formData.include_rule).some((checked) => checked),
      },
    ],
    symbols_allowed: [
      {
        trigger: 'blur',
        message: t('请指定特殊字符'),
        validator: (value: string) => {
          if (formData.include_rule.symbols) {
            return !!value;
          }
          return true;
        },
      },
      {
        trigger: 'blur',
        message: t('特殊字符不允许包含空格'),
        validator: (value: string) => {
          if (formData.include_rule.symbols) {
            return !/\s/.test(value);
          }
          return true;
        },
      },
      {
        trigger: 'blur',
        message: t('请输入除大小写字母、数字外的英文半角字符'),
        validator: (value: string) => {
          if (formData.include_rule.symbols) {
            return /^[\u0021-\u002f\u003a-\u0040\u005b-\u0060\u007b-\u007e]+$/.test(value);
          }
          return true;
        },
      },
    ],
  };

  const defaultConfig = reactive(initData());
  const formRef = ref();
  const formData = reactive(initData());
  const excludeContinuousRule = shallowRef({
    keyboards: [] as string[],
    letters: [] as string[],
    numbers: [] as string[],
    symbols: [] as string[],
    repeats: [] as string[],
  });
  let message = '';

  const typeMaxCount = computed(() => Object.values(formData.include_rule).filter((item) => item).length);

  const { run: getPasswordPolicyRun, loading: isLoading } = useRequest(getPasswordPolicy, {
    manual: true,
    onSuccess: (data) => {
      const { id, name, rule } = data;
      passwordPolicyData.id = id;
      passwordPolicyData.name = name;
      Object.assign(defaultConfig, rule);
      Object.assign(formData, rule);
      const { repeats } = rule;
      excludeContinuousRule.value = {
        keyboards: ['123456789'.slice(9 - repeats)],
        letters: ['abcdefghijklmnopqrstuvwxyz'.slice(0, repeats)],
        numbers: ['1234567890'.slice(0, repeats)],
        symbols: ['!#%&()*+,-./;<=>?[]^_{|}~@:$'.slice(0, repeats)],
        repeats: ['a', '2', '@'].map((char) => char.repeat(repeats)),
      };
    },
  });

  const fetchData = () => {
    getPasswordPolicyRun({
      name: props.dbType === DBTypes.REDIS ? 'redis_password_v2' : `${props.dbType}_password`,
    });
  };

  const { run: updatePasswordPolicyRun, loading: isSubmitting } = useRequest(updatePasswordPolicy, {
    manual: true,
    onSuccess: () => {
      Message({
        theme: 'success',
        message,
      });
      fetchData();
    },
  });

  watch(
    () => props.dbType,
    () => {
      fetchData();
    },
  );

  const handleChangeIncludeRule = () => {
    formData.number_of_types = typeMaxCount.value;
    formRef.value.validate();
  };

  const handleSubmit = async (reset = false) => {
    if (!reset) {
      await formRef.value.validate();
      message = t('保存成功');
    } else {
      message = t('重置成功');
      formRef.value.clearValidate();
    }
    updatePasswordPolicyRun({
      ...passwordPolicyData,
      rule: {
        ...formData,
        symbols_allowed: _.uniq(formData.symbols_allowed.split('')).join(''),
      },
      reset,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultConfig);
    handleSubmit(true);
  };
</script>

<style lang="less" scoped>
  .password-policy {
    font-size: @font-size-mini;

    .password-policy-number {
      width: 68px;
    }

    .password-policy-input-box {
      display: flex;
      width: 448px;
      padding: 16px;
      background: #f5f7fa;

      .input-prefix {
        width: 88px;
        height: 32px;
        text-align: center;
        background: #fafbfd;
        border: 1px solid #c4c6cc;
        border-right: none;
        border-radius: 0 2px 2px 0;
      }

      .symbols-input {
        flex: 1;
      }
    }

    .password-policy-weak {
      display: flex;
      align-items: center;
    }

    .password-policy-rules {
      width: 538px;
      padding: 6px 26px;
      background: #f5f7fa;

      li {
        list-style: initial !important;
      }
    }

    .password-policy-footer {
      margin: 32px 0 0 24px;

      .bk-button {
        width: 88px;
      }
    }
  }
</style>
