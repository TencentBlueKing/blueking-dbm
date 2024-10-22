<template>
  <BkFormItem
    :label="t('账号名')"
    property="user"
    required>
    <BkSelect
      v-model="user"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading">
      <BkOption
        v-for="item of accounts"
        :key="item.account.account_id"
        :label="item.account.user"
        :value="item.account.user" />
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getPermissionRules as getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { getPermissionRules as getMysqlPermissionRules } from '@services/source/mysqlPermissionAccount';
  import { getPermissionRules as getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import type { PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  interface Props {
    accountType: AccountTypes;
  }

  interface Emits {
    (e: 'change', data: PermissionRule['rules']): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const user = defineModel<string>('modelValue', {
    default: '',
  });

  const { t } = useI18n();

  const isLoading = ref(false);
  const accounts = ref<PermissionRule[]>([]);

  const updateAccoutRules = () => {
    emits('change', accounts.value.find((item) => item.account.user === user.value)?.rules || []);
  };

  watch(user, updateAccoutRules);

  /**
   * 获取账号信息
   */
  const fetchAccounts = async () => {
    const apiMap = {
      [AccountTypes.MYSQL]: getMysqlPermissionRules,
      [AccountTypes.TENDBCLUSTER]: getMysqlPermissionRules,
      [AccountTypes.MONGODB]: getMongodbPermissionRules,
      [AccountTypes.SQLSERVER]: getSqlserverPermissionRules,
    };

    try {
      isLoading.value = true;
      const { results } = await apiMap[props.accountType]({
        offset: 0,
        limit: -1,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        account_type: props.accountType,
      });
      accounts.value = results;
      updateAccoutRules();
    } finally {
      isLoading.value = false;
    }
  };

  fetchAccounts();
</script>
