<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
    render-directive="if"
    :title="t('添加授权规则')"
    :width="840"
    @closed="handleClose">
    <DbForm
      ref="formRef"
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
          :input-search="false">
          <BkOption
            v-for="item of accoutList"
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
          v-model="formData.access_db"
          :placeholder="t('请输入DB名称_可以使用通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔')"
          :rows="3"
          type="textarea" />
      </BkFormItem>
      <BkFormItem
        class="rule-form-item"
        :label="t('权限设置')"
        property="auth">
        <div class="rule-setting-box">
          <BkFormItem :label="t('数据库读写权限(DML)')">
            <div class="rule-form-row">
              <BkCheckbox
                v-model="allChecked"
                v-bk-tooltips="{
                  content: t('你已选择所有权限'),
                  disabled: !checkAllPrivileges,
                }"
                class="check-all"
                :disabled="checkAllPrivileges"
                :indeterminate="!!formData.privilege.length && formData.privilege.length !== dbOperations.dml.length"
                @change="(value: boolean) => handleSelectedAll(value)">
                {{ t('全选') }}
              </BkCheckbox>
              <BkCheckboxGroup
                v-model="formData.privilege"
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
        </div>
        <div
          class="rule-setting-box"
          style="margin-top: 16px">
          <BkFormItem
            class="mb-0"
            :label="t('数据库所有者权限(owner)')">
            <BkCheckbox
              :model-value="checkAllPrivileges"
              @change="(value: boolean) => handleSelectAllPrivileges(value)">
              db_owner ( {{ t('包含所有权限，其他权限无需授予') }} )
            </BkCheckbox>
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
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { addAccountRule, getPermissionRules, queryAccountRules } from '@services/source/sqlserverPermissionAccount';

  import DbForm from '@components/db-form/index.vue';

  import { messageSuccess } from '@utils';

  import dbOperations from './config';

  import { AccountTypes } from '@/common/const';

  interface Props {
    accountId: number;
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountId: -1,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const formRef = ref<InstanceType<typeof DbForm>>();
  const checkAllPrivileges = ref(false);
  const existDBs = ref<string[]>([]);

  const { t } = useI18n();

  /**
   * 初始化表单数据
   */
  const initFormdata = () => ({
    account_id: 0,
    access_db: '',
    privilege: [] as string[],
  });

  const rules = {
    auth: [
      {
        trigger: 'change',
        message: t('请设置权限'),
        validator: () => formData.privilege.length || checkAllPrivileges.value,
      },
    ],
    access_db: [
      {
        required: true,
        trigger: 'blur',
        message: t('访问DB不能为空'),
        validator: (value: string) => !!value && !!value.trim(),
      },
      {
        trigger: 'blur',
        message: t('DB名称支持通配符_如Data_区分大小写_多个使用英文逗号_分号或换行分隔'),
        validator: (value: string) => {
          const dbs = value.split(/[\n;,]/);
          return _.every(dbs, (item) => (!item ? true : /^[0-9a-zA-Z][0-9a-zA-Z%]*$/.test(item)));
        },
      },
      {
        trigger: 'blur',
        message: () => t('该账号下已存在xx规则', [existDBs.value.join('，')]),
        validator: () => {
          existDBs.value = [];

          const userInfo = accoutList.value.find((item) => item.account_id === formData.account_id);
          const dbs = formData.access_db
            .replace(/\n|;/g, ',')
            .split(',')
            .filter((db) => db);

          if (!userInfo || dbs.length === 0) {
            return false;
          }

          return queryAccountRules({
            user: userInfo.user,
            access_dbs: dbs,
            account_type: AccountTypes.SQLSERVER,
          }).then((res) => {
            const rules = res.results[0]?.rules || [];
            existDBs.value = rules.map((item) => item.access_db);
            return rules.length === 0;
          });
        },
      },
    ],
  };

  const formData = reactive(initFormdata());

  const allChecked = computed(() => formData.privilege.length === dbOperations.dml.length);
  const accoutList = computed(() =>
    (sqlPermissonRules.value?.results || []).map((permissionItem) => ({
      account_id: permissionItem.account.account_id,
      user: permissionItem.account.user,
    })),
  );

  const { data: sqlPermissonRules, run: getPermissionRulesRun } = useRequest(getPermissionRules, {
    manual: true,
  });

  const { loading: isSubmitting, run: addSqlserverAccountRuleRun } = useRequest(addAccountRule, {
    manual: true,
    onSuccess() {
      messageSuccess(t('成功添加授权规则'));
      emits('success');
      window.changeConfirm = false;
      handleClose();
    },
  });

  const handleSelectAllPrivileges = (checked: boolean) => {
    checkAllPrivileges.value = checked;
    if (checked) {
      formData.privilege = [];
    }
  };

  /**
   * 初始化
   */
  watch(isShow, () => {
    if (isShow.value) {
      formData.account_id = props.accountId;
      getPermissionRulesRun({
        offset: 0,
        limit: -1,
        account_type: AccountTypes.SQLSERVER,
      });
    }
  });

  const handleSelectedAll = (value: boolean) => {
    if (value) {
      formData.privilege = dbOperations.dml;
      return;
    }

    formData.privilege = [];
  };

  const handleBeforeClose = () => {
    if (window.changeConfirm) {
      return new Promise<boolean>((resolve) => {
        InfoBox({
          title: t('确认离开当前页'),
          content: t('离开将会导致未保存信息丢失'),
          confirmText: t('离开'),
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
    if (!result) {
      return;
    }
    isShow.value = false;
    _.merge(formData, initFormdata());
    checkAllPrivileges.value = false;
    existDBs.value = [];
    window.changeConfirm = false;
  };

  /**
   * 提交功能
   */
  const handleSubmit = async () => {
    await formRef.value!.validate();
    const params = {
      access_db: formData.access_db.replace(/\n|;/g, ','), // 统一分隔符
      privilege: {},
      account_id: formData.account_id,
      account_type: AccountTypes.SQLSERVER,
    };
    if (checkAllPrivileges.value) {
      Object.assign(params.privilege, {
        sqlserver_owner: ['db_owner'],
      });
    } else {
      Object.assign(params.privilege, {
        sqlserver_dml: formData.privilege,
      });
    }
    addSqlserverAccountRuleRun(params);
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

    .rule-form-textarea {
      height: var(--height);
      max-height: 160px;
      min-height: 32px;

      :deep(textarea) {
        line-height: 1.8;
      }
    }

    .rule-form-item {
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
          margin-right: 35px;
          margin-bottom: 16px;
          margin-left: 0;
        }
      }

      .check-all {
        position: relative;
        width: 50px;
        margin-right: 48px;

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
