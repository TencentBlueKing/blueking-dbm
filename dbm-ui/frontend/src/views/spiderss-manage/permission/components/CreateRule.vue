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
      :model="formdata"
      :rules="rules">
      <BkFormItem
        :label="$t('账号名')"
        property="account_id"
        required>
        <BkSelect
          v-model="formdata.account_id"
          :clearable="false"
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
        :label="$t('访问DB')"
        property="access_db"
        required
        :rules="rules.access_db">
        <DbTextarea
          ref="textareaRef"
          v-model="formdata.access_db"
          :max-height="400"
          :placeholder="$t('请输入DB名称_可以使用通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔')"
          :teleport-to-body="false" />
      </BkFormItem>
      <BkFormItem
        class="rule-form__item privilege"
        :label="$t('权限设置')"
        property="auth"
        :required="false">
        <BkFormItem
          label="DML"
          required>
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('dml')"
            :model-value="getAllCheckedboxValue('dml')"
            @change="(value: boolean) => handleSelectedAll('dml', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="formdata.privilege.dml"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="option of dbOperations.dml"
              :key="option"
              :label="option">
              {{ option }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem
          label="DDL"
          required>
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('ddl')"
            :model-value="getAllCheckedboxValue('ddl')"
            @change="(value: boolean) => handleSelectedAll('ddl', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="formdata.privilege.ddl"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="option of dbOperations.ddl"
              :key="option"
              :label="option">
              {{ option }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem
          label="GLOBAL"
          required>
          <BkCheckbox
            class="check-all"
            :indeterminate="getAllCheckedboxIndeterminate('glob')"
            :model-value="getAllCheckedboxValue('glob')"
            @change="(value: boolean) => handleSelectedAll('glob', value)">
            {{ $t('全选') }}
          </BkCheckbox>
          <BkCheckboxGroup
            v-model="formdata.privilege.glob"
            class="rule-form__checkbox-group">
            <BkCheckbox
              v-for="option of dbOperations.glob"
              :key="option"
              :label="option">
              {{ option }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import type { AccountRule, PermissionRuleAccount } from '@services/spider/permission';
  import { createAccountRule, getPermissionRules, queryAccountRules } from '@services/spider/permission';

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { dbOperations } from '../common/consts';
  type AuthItemKey = keyof typeof dbOperations;

  import { AccountTypes } from '@common/const';

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
  const { currentBizId } = globalbizsStore;
  const { TENDBCLUSTER } = AccountTypes;

  const ruleRef = ref();

  watch(() => props.isShow, (show) => {
    if (show) {
      formdata.account_id = props.accountId ?? -1;
      getAccount();
    }
  });

  const initFormdata = (): AccountRule =>  ({
    account_id: null,
    access_db: '',
    privilege: {
      ddl: [],
      dml: [],
      glob: [],
    },
  });

  const verifyAccountRuleFormat = () => formdata.access_db
    .replace(/[,;\r\n]/g, ',')
    .split(',')
    .every(db => /^[a-zA-Z]*%?$/g.test(db));

  const verifyAccountRulesExits = () => {
    existDBs.value = [];

    const user = selectedUserInfo.value?.user;
    const dbs = formdata.access_db.replace(/[,;\r\n]/g, ',')
      .split(',')
      .filter(db => db);

    if (!user || dbs.length === 0) return false;

    return queryAccountRules({
      user,
      access_dbs: dbs,
      account_type: TENDBCLUSTER,
    })
      .then((res) => {
        const rules = res.results[0]?.rules || [];
        existDBs.value = rules.map(item => item.access_db);

        return rules.length === 0;
      });
  };

  let formdata = reactive(initFormdata());
  const accounts = ref<PermissionRuleAccount[]>([]);
  const isLoading = ref(false);
  const isSubmitting = ref(false);
  const existDBs = ref<string[]>([]);

  const selectedUserInfo = computed(() => accounts.value.find(item => item.account_id === formdata.account_id));
  const rules = {
    auth: [
      {
        trigger: 'change',
        message: t('请设置权限'),
        validator: () => {
          const { ddl, dml, glob } = formdata.privilege;
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
        message: t('访问DB格式错误'),
        validator: verifyAccountRuleFormat,
      },
      {
        trigger: 'blur',
        message: () => t('该账号下已存在xx规则', [existDBs.value.join('，')]),
        validator: verifyAccountRulesExits,
      },
    ],
  };

  const getAccount = () => {
    isLoading.value = true;
    getPermissionRules({
      bk_biz_id: currentBizId,
      account_type: TENDBCLUSTER,
    })
      .then((res) => {
        accounts.value = res.results.map(item => item.account);
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const getAllCheckedboxValue = (key: AuthItemKey) => formdata.privilege[key].length === dbOperations[key].length;

  const getAllCheckedboxIndeterminate = (key: AuthItemKey) => (
    formdata.privilege[key].length > 0
    && formdata.privilege[key].length !== dbOperations[key].length
  );

  const handleSelectedAll = (key: AuthItemKey, value: boolean) => {
    if (value) {
      formdata.privilege[key] = [...dbOperations[key]];
      return;
    }

    formdata.privilege[key] = [];
  };

  const handleBeforeClose = () => {
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
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();

    if (!result) return;

    emits('update:isShow', false);
    formdata = initFormdata();
    existDBs.value = [];
    window.changeConfirm = false;
  };

  async function handleSubmit() {
    await ruleRef.value.validate();

    isSubmitting.value = true;
    const params = {
      ...formdata,
      access_db: formdata.access_db.replace(/[,;\r\n]/g, ','), // 统一分隔符
      account_type: TENDBCLUSTER,
    };
    createAccountRule(params)
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
        isSubmitting.value = false;
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

    :deep(.privilege > .bk-form-label::after) {
      display: none;
    }

  }
</style>
