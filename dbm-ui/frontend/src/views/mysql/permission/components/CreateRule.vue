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
    :is-show="props.isShow"
    :title="$t('添加授权规则')"
    :width="640"
    @closed="handleClose">
    <DbForm
      ref="ruleRef"
      class="rule-form"
      form-type="vertical"
      :model="state.formdata"
      :rules="rules">
      <BkFormItem
        :label="$t('账号名')"
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
        :label="$t('访问DB')"
        property="access_db"
        required
        :rules="rules.access_db">
        <DbTextarea
          ref="textareaRef"
          v-model="state.formdata.access_db"
          :max-height="400"
          :placeholder="$t('请输入DB名称_可以使用通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔')"
          :teleport-to-body="false" />
      </BkFormItem>
      <BkFormItem
        class="rule-form__item"
        :label="$t('权限设置')"
        property="auth">
        <BkFormItem label="DML">
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('dml')"
            :model-value="getAllCheckedboxValue('dml')"
            @change="(value: boolean) => handleSelectedAll('dml', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="state.formdata.privilege.dml"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="type of dbOperations.dml"
              :key="type"
              :label="type">
              {{ type }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem label="DDL">
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('ddl')"
            :model-value="getAllCheckedboxValue('ddl')"
            @change="(value: boolean) => handleSelectedAll('ddl', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="state.formdata.privilege.ddl"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="type of dbOperations.ddl"
              :key="type"
              :label="type">
              {{ type }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem
          class="mb-0"
          label="GLOBAL">
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('glob')"
            :model-value="getAllCheckedboxValue('glob')"
            @change="(value: boolean) => handleSelectedAll('glob', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="state.formdata.privilege.glob"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="type of dbOperations.glob"
              :key="type"
              :label="type" />
          </BkCheckboxGroup>
        </BkFormItem>
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="state.isSubmitting"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { createAccountRule, getPermissionRules, queryAccountRules } from '@services/permission';
  import type { AccountRule, PermissionRuleAccount } from '@services/types/permission';

  import { useInfo, useStickyFooter  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { dbOperations } from '../common/const';

  type AuthItemKey = keyof typeof dbOperations;

  const props = defineProps({
    isShow: {
      type: Boolean,
      default: false,
    },
    accountId: {
      type: Number,
      default: -1,
    },
  });
  const emits = defineEmits(['update:isShow', 'success']);

  const { t } = useI18n();
  const globalbizsStore = useGlobalBizs();

  const ruleRef = ref();
  /** 设置底部按钮粘性布局 */
  useStickyFooter(ruleRef);

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
          return ddl.length !== 0 || dml.length !== 0 || glob.length !== 0;
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

  /**
   * 初始化表单数据
   */
  function initFormdata(): AccountRule {
    return {
      account_id: null,
      access_db: '',
      privilege: {
        ddl: [],
        dml: [],
        glob: [],
      },
    };
  }

  /**
   * 初始化
   */
  watch(() => props.isShow, (show) => {
    if (show) {
      state.formdata.account_id = props.accountId ?? -1;
      getAccount();
    }
  });

  /**
   * get textarea height
   */
  const textareaRef = ref();
  const textareaHeight = ref(0);
  watch(() => state.formdata.access_db, getTextareaHeight);
  function getTextareaHeight() {
    textareaHeight.value = 0;

    if (textareaRef.value) {
      const el = textareaRef.value.$el as HTMLDivElement;
      textareaHeight.value = el.firstElementChild?.scrollHeight ?? 0;
    }
  }

  function verifyAccountRules() {
    const user = selectedUserInfo.value?.user;
    const dbs = state.formdata.access_db.replace(/\n|;/g, ',')
      .split(',')
      .filter(db => db);

    if (!user || dbs.length === 0) return false;

    return queryAccountRules(globalbizsStore.currentBizId, {
      user,
      access_dbs: dbs,
    })
      .then((res) => {
        const rules = res.results[0]?.rules || [];
        state.existDBs = rules.map(item => item.access_db);
        return rules.length === 0;
      });
  }

  /**
   * 获取账号列表
   */
  function getAccount() {
    state.isLoading = true;
    getPermissionRules({ bk_biz_id: globalbizsStore.currentBizId })
      .then((res) => {
        state.accounts = res.results.map(item => item.account);
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleBeforeClose() {
    if (window.changeConfirm) {
      return new Promise((resolve) => {
        useInfo({
          title: t('确认离开当前页'),
          content: t('离开将会导致未保存信息丢失'),
          confirmTxt: t('离开'),
          onConfirm: () => {
            window.changeConfirm = false;
            resolve(true);
            return true;
          },
        });
      });
    }
    return true;
  }

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    emits('update:isShow', false);
    state.formdata = initFormdata();
    state.existDBs = [];
    window.changeConfirm = false;
  }

  /**
   * 提交功能
   */
  async function handleSubmit() {
    await ruleRef.value.validate();

    state.isSubmitting = true;
    const params = {
      ...state.formdata,
      access_db: state.formdata.access_db.replace(/\n|;/g, ','), // 统一分隔符
    };
    createAccountRule(globalbizsStore.currentBizId, params)
      .then(() => {
        Message({
          message: t('成功添加授权规则'),
          theme: 'success',
          delay: 1500,
        });
        emits('success');
        window.changeConfirm = false;
        handleClose();
      })
      .finally(() => {
        state.isSubmitting = false;
      });
  }

</script>

<style lang="less" scoped>
  .rule-form {
    padding: 24px 40px 40px;

    &__textarea {
      height: var(--height);
      max-height: 160px;
      min-height: 32px;

      :deep(textarea) {
        line-height: 1.8;
      }
    }

    &__item {
      > :deep(.bk-form-label) {
        font-weight: bold;
        color: @title-color;

        &::after {
          position: absolute;
          top: 0;
          width: 14px;
          line-height: 32px;
          color: @danger-color;
          text-align: center;
          content: "*";
        }
      }
    }

    &__checkbox-group {
      padding: 7px 0;
      line-height: normal;
    }

    .check-all {
      position: relative;
      margin-right: 48px;

      :deep(.bk-checkbox-label) {
        font-weight: bold;
      }

      &::after {
        position: absolute;
        top: 50%;
        right: -24px;
        width: 1px;
        height: 14px;
        background-color: #c4c6cc;
        content: "";
        transform: translateY(-50%);
      }
    }
  }
</style>
