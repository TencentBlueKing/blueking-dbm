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
  <BkLoading :loading="loading">
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
        :rules="rules">
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
          v-model="formData.timeData.monthDateValue"
          class="group-item date-selector"
          :clearable="false"
          :popover-options="{
            extCls: 'password-randomization-date-selector-popover'
          }">
          <BkOption
            v-for="(item, index) in 31"
            :key="index"
            :label="`${item}${t('号')}`"
            :value="item">
            {{ item }}
          </BkOption>
        </BkSelect>
        <BkTimePicker
          v-model="formData.timeData.dateValue"
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
                {{ passwordPolicyData?.min_length }} ~ {{ passwordPolicyData?.max_length }} {{ t('位') }}
              </span>
            </div>
            <div class="complexity-item">
              {{ t('密码必须包含') }}：
              <span class="complexity-item-value">
                {{ complexity.contains }}
              </span>
            </div>
            <div class="complexity-item">
              {{ t('密码不允许连续n位出现', [passwordPolicyData?.follow.limit]) }}：
              <span class="complexity-item-value">
                {{ complexity.follows }}
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
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getPasswordPolicy } from '@services/permission';

  const { t } = useI18n();

  const initData = () => ({
    typeValue: 'month',
    weekValue: [],
    monthDateValue: 1,
    dateValue: '00:00',
  });

  const formData = reactive({
    password: '',
    timeData: initData(),
  });
  const passwordVisible = ref(false);
  const unVisiblePassword = computed(() => '*'.repeat(formData.password.length));
  const typeValue = computed(() => formData.timeData.typeValue);
  const typeOptions = ref([
    {
      value: 'day',
      label: t('每天'),
    },
    {
      value: 'week',
      label: t('每周'),
    },
    {
      value: 'month',
      label: t('每月'),
    },
  ]);
  const weekOptions = ref([
    {
      value: 'monday',
      label: t('周一'),
    },
    {
      value: 'tuesday',
      label: t('周二'),
    },
    {
      value: 'wendesday',
      label: t('周三'),
    },
    {
      value: 'thursday',
      label: t('周四'),
    },
    {
      value: 'friday',
      label: t('周五'),
    },
    {
      value: 'saturday',
      label: t('周六'),
    },
    {
      value: 'sundy',
      label: t('周日'),
    },
  ]);

  const complexity = reactive({} as {
    contains: string,
    follows: string
  });

  const formRef = ref();
  const rules = [
    {
      required: true,
      message: t('请选择'),
      validator() {
        const {
          typeValue,
          weekValue,
          monthDateValue,
          dateValue,
        } = formData.timeData;

        if (typeValue === 'day') {
          return dateValue !== '';
        }
        if (typeValue === 'week') {
          return weekValue.length > 0 && dateValue !== '';
        }
        if (typeValue === 'month') {
          return monthDateValue && dateValue !== '';
        }

        return true;
      },
    },
  ];

  const POLICY_MAP: {
    contains: Record<string, string>
    follows: Record<string, string>
  } = {
    contains: {
      uppercase: t('大写字母'),
      lowercase: t('小写字母'),
      numbers: t('数字'),
      symbols: t('特殊字符_除空格外'),
    },
    follows: {
      keyboards: t('键盘序'),
      letters: t('字母序'),
      numbers: t('数字序'),
      repeats: t('连续特殊符号序'),
      symbols: t('重复字母_数字_特殊符号'),
    },
  };

  const {
    data: passwordPolicyData,
    loading,
  } = useRequest(getPasswordPolicy, {
    defaultParams: ['mysql'],
    onSuccess(res) {
      const contains = Object.keys(POLICY_MAP.contains).reduce((prev, current) => {
        if (res[current]) {
          prev.push(POLICY_MAP.contains[current]);
        }

        return prev;
      }, [] as string[]);

      const follows = Object.keys(POLICY_MAP.follows).reduce((prev, current) => {
        if (res.follow[current]) {
          prev.push(POLICY_MAP.follows[current]);
        }

        return prev;
      }, [] as string[]);

      complexity.contains = contains.join('、');
      complexity.follows = follows.join('、');
    },
  });

  const handleReset = () => {
    Object.assign(formData.timeData, initData());
    handleSubmit(t('重置成功'));
  };

  const handleSubmit = async (message = t('保存成功')) => {
    await formRef.value.validate();
  };
</script>

<style lang="less" scoped>
  .password-randomization {
    font-size: @font-size-mini;
    background-color: #FFFFFF;
    padding: 32px 0;

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
      border: 1px solid #DCDEE5;
      border-radius: 2px;
      display: inline-block;

      .complexity-head {
        border-bottom: 1px solid #DCDEE5;
        padding-left: 16px;
        color: #63656E;
        font-weight: 700;
        background-color: #FAFBFD;
      }

      .complexity-content {
        padding: 12px 16px 12px 32px;

        .complexity-item {
          height: 32px;
          line-height: 32px;
          position: relative;

          &::before {
            content: '';
            position: absolute;
            top: 14px;
            left: -13px;
            width: 4px;
            height: 4px;
            display: block;
            border-radius: 50%;
            background: #979BA5;
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
  }
</style>
