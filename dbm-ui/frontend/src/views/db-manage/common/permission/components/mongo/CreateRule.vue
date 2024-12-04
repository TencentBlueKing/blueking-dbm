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
    :title="t('添加授权规则')"
    :width="640"
    @closed="handleClose">
    <DbForm
      ref="ruleRef"
      class="rule-form"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <BkFormItem
        :label="t('账号名')"
        property="account_id"
        required>
        <BkSelect
          v-model="formData.account_id"
          :clearable="false"
          filterable
          :input-search="false"
          :loading="getPermissionRulesLoading">
          <BkOption
            v-for="item of accounts"
            :key="item.account_id"
            :label="item.user"
            :value="item.account_id" />
        </BkSelect>
      </BkFormItem>
      <BkFormItem
        :label="t('访问DB')"
        required>
        <BkRadioGroup
          v-model="accessDBType"
          @change="handleAccessDBTypeChange">
          <BkRadio label="admin" />
          <BkRadio label="not_admin">{{ t('非 admin') }}</BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        v-if="accessDBType === 'not_admin'"
        :label="t('DB 名')"
        property="access_db"
        required
        :rules="rules.access_db">
        <BkInput
          v-model="formData.access_db"
          :maxlength="100"
          :placeholder="t('请输入访问DB名_以字母开头_支持字母_数字_下划线_多个使用英文逗号_分号或换行分隔')"
          :rows="4"
          type="textarea" />
      </BkFormItem>
      <BkFormItem
        class="form-item privilege"
        :label="t('权限设置')"
        property="privilege"
        :required="false">
        <div class="rule-setting-box">
          <BkFormItem
            :label="t('用户权限')"
            required>
            <div class="rule-form-row">
              <BkCheckbox
                class="check-all"
                :indeterminate="getAllCheckedboxIndeterminate('mongo_user')"
                :model-value="getAllCheckedboxValue('mongo_user')"
                @change="(value: boolean) => handleSelectedAll('mongo_user', value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formData.privilege.mongo_user"
                class="checkbox-group">
                <BkCheckbox
                  v-for="option of mongoUserDbOperations"
                  :key="option"
                  :label="option">
                  {{ option }}
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
          <BkFormItem
            v-if="accessDBType === 'admin'"
            :label="t('管理权限')"
            required>
            <div class="rule-form-row">
              <BkCheckbox
                class="check-all"
                :indeterminate="getAllCheckedboxIndeterminate('mongo_manager')"
                :model-value="getAllCheckedboxValue('mongo_manager')"
                @change="(value: boolean) => handleSelectedAll('mongo_manager', value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formData.privilege.mongo_manager"
                class="checkbox-group">
                <BkCheckbox
                  v-for="option of dbOperations.mongo_manager"
                  :key="option"
                  :label="option">
                  {{ option }}
                </BkCheckbox>
              </BkCheckboxGroup>
            </div>
          </BkFormItem>
        </div>
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { addAccountRule, getPermissionRules, queryAccountRules } from '@services/source/mongodbPermissionAccount';
  import type { PermissionRuleAccount } from '@services/types/permission';

  import { useBeforeClose } from '@hooks';

  import { AccountTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';

  import { messageSuccess } from '@utils';

  import dbOperations from './config';

  type AuthItemKey = 'mongo_user' | 'mongo_manager';

  interface Props {
    accountId: number;
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
  const handleBeforeClose = useBeforeClose();

  const ruleRef = ref<InstanceType<typeof DbForm>>();
  const accounts = ref<PermissionRuleAccount[]>([]);
  const existDBs = ref<string[]>([]);
  const accessDBType = ref<'admin' | 'not_admin'>('admin');

  const replaceReg = /[,;\r\n]/g;

  const initFormData = () => ({
    account_id: -1,
    access_db: 'admin',
    privilege: {
      mongo_user: [] as string[],
      mongo_manager: [] as string[],
    },
  });

  const rules = {
    privilege: [
      {
        trigger: 'change',
        message: t('请设置权限'),
        validator: () => {
          const { mongo_user: mongoUser, mongo_manager: mongoManager } = formData.privilege;
          return mongoUser.length !== 0 || mongoManager.length !== 0;
        },
      },
    ],
    access_db: [
      {
        required: true,
        trigger: 'blur',
        message: t('访问 DB 不能为空'),
        validator: (value: string) => {
          const dbs = value.split(/[\n;,]/);
          return _.every(dbs, (item) => !!item.trim());
        },
      },
      {
        required: true,
        trigger: 'blur',
        message: t('访问 DB 名不允许为 admin'),
        validator: (value: string) => /^(?!admin$).*/.test(value),
      },
      {
        required: true,
        trigger: 'blur',
        message: t('请输入访问DB名_以字母开头_支持字母_数字_下划线_多个使用英文逗号_分号或换行分隔'),
        validator: (value: string) => {
          const dbs = value.split(/[\n;,]/);
          return _.every(dbs, (item) => (!item ? true : /^[A-Za-z][A-Za-z0-9_]*$/.test(item)));
        },
      },
      {
        required: true,
        trigger: 'blur',
        message: () => t('该账号下已存在xx规则', [existDBs.value.join(',')]),
        validator: () => {
          existDBs.value = [];
          const user = accounts.value.find((item) => item.account_id === formData.account_id)?.user;
          const dbs = formData.access_db
            .replace(replaceReg, ',')
            .split(',')
            .filter((db) => db !== '');
          if (!user || dbs.length === 0) {
            return false;
          }
          return queryAccountRules({
            user,
            access_dbs: dbs,
            account_type: AccountTypes.MONGODB,
          }).then((res) => {
            const rules = res.results[0]?.rules || [];
            existDBs.value = rules.map((item) => item.access_db);
            return rules.length === 0;
          });
        },
      },
    ],
  };

  const formData = reactive(initFormData());

  const mongoUserDbOperations = computed(() =>
    accessDBType.value === 'not_admin' ? ['read', 'readWrite'] : dbOperations.mongo_user,
  );

  const { run: getPermissionRulesRun, loading: getPermissionRulesLoading } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess(permissionRules) {
      accounts.value = permissionRules.results.map((item) => item.account);
    },
  });

  const { run: addMongodbAccountRuleRun, loading: isSubmitting } = useRequest(addAccountRule, {
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
      formData.account_id = props.accountId ?? -1;
      getPermissionRulesRun({
        offset: 0,
        limit: -1,
        account_type: AccountTypes.MONGODB,
      });
    }
  });

  const getAllCheckedboxValue = (key: AuthItemKey) => formData.privilege[key].length === dbOperations[key].length;

  const getAllCheckedboxIndeterminate = (key: AuthItemKey) =>
    formData.privilege[key].length > 0 && formData.privilege[key].length !== dbOperations[key].length;

  const handleSelectedAll = (key: AuthItemKey, value: boolean) => {
    if (value) {
      formData.privilege[key] = dbOperations[key];
      return;
    }

    formData.privilege[key] = [];
  };

  const handleAccessDBTypeChange = (value: 'admin' | 'not_admin') => {
    formData.access_db = value === 'admin' ? 'admin' : '';
    formData.privilege.mongo_user = [];
    formData.privilege.mongo_manager = [];
  };

  const handleClose = async () => {
    const result = await handleBeforeClose();

    if (!result) {
      return;
    }

    isShow.value = false;
    _.merge(formData, initFormData());
    accessDBType.value = 'admin';
    existDBs.value = [];
    window.changeConfirm = false;
  };

  const handleSubmit = async () => {
    await ruleRef.value!.validate();
    const params = {
      ...formData,
      access_db: formData.access_db.replace(replaceReg, ','), // 统一分隔符
      account_type: AccountTypes.MONGODB,
    };
    addMongodbAccountRuleRun(params);
  };
</script>

<style lang="less" scoped>
  .rule-form {
    padding: 24px;

    .rule-setting-box {
      padding: 16px;
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
          margin-right: 35px;
          margin-bottom: 16px;
          margin-left: 0;
        }
      }

      .check-all {
        position: relative;
        width: 50px;
        margin-right: 50px;

        :deep(.bk-checkbox-label) {
          font-weight: bold;
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
