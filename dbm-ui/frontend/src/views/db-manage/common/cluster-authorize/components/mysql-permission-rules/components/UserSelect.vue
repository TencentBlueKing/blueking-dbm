<template>
  <BkFormItem
    :label="t('账号名')"
    property="user"
    required>
    <BkSelect
      v-model="user"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      :loading="isLoading">
      <BkOption
        v-for="item of accounts"
        :key="item.account.account_id"
        :label="item.account.user"
        :value="item.account.user" />
      <template #extension>
        <div
          class="default-display-main"
          @click="handleCreateAccount">
          <DbIcon
            class="add-account-icon"
            type="plus-circle" />
          <span>{{ t('新建账号') }}</span>
        </div>
      </template>
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import type { RouteLocationRaw } from 'vue-router';

  import { getPermissionRules as getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { getPermissionRules as getMysqlPermissionRules } from '@services/source/mysqlPermissionAccount';
  import { getPermissionRules as getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import type { PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  interface Props {
    accountType: AccountTypes;
    disabled?: boolean;
  }

  type Emits = (e: 'change', data: PermissionRule['rules']) => void;

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const user = defineModel<string>('modelValue', {
    default: '',
  });

  const { t } = useI18n();
  const router = useRouter();

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
      [AccountTypes.MONGODB]: getMongodbPermissionRules,
      [AccountTypes.MYSQL]: getMysqlPermissionRules,
      [AccountTypes.SQLSERVER]: getSqlserverPermissionRules,
      [AccountTypes.TENDBCLUSTER]: getMysqlPermissionRules,
    };

    try {
      isLoading.value = true;
      const { results } = await apiMap[props.accountType]({
        account_type: props.accountType,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        limit: -1,
        offset: 0,
      });
      accounts.value = results;
      updateAccoutRules();
    } finally {
      isLoading.value = false;
    }
  };

  fetchAccounts();

  /**
   * 新建账号 - 跳转到授权管理列表页并弹出新建账号弹窗
   */
  const routeNameMap: Record<AccountTypes, string> = {
    [AccountTypes.MONGODB]: 'MongodbPermission',
    [AccountTypes.MYSQL]: 'PermissionRules',
    [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules',
    [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
  };

  const handleCreateAccount = () => {
    const route: RouteLocationRaw = {
      name: routeNameMap[props.accountType],
      query: {
        action: 'create_account',
      },
    };
    const routeData = router.resolve(route);
    window.open(routeData.href, '_blank');
  };
</script>
<style lang="less">
  .default-display-main {
    font-family: MicrosoftYaHei, Arial, sans-serif;
    color: #4d4f56;
    cursor: pointer;
    margin-left: 10px;

    .add-account-icon {
      margin-right: 5px;
      font-size: 14px;
      color: #979ba5;
    }
  }
</style>
