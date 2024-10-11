<template>
  <BkFormItem
    :label="t('账号名')"
    property="user"
    required>
    <BkSelect
      v-model="modelValue"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading">
      <BkOption
        v-for="item of accountRules"
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
    (e: 'success', data: PermissionRule[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>('modelValue', {
    default: '',
  });

  const { t } = useI18n();

  const isLoading = ref(false);
  const accountRules = ref<PermissionRule[]>([]);

  /**
   * 获取账号信息
   */
  const getAccount = () => {
    isLoading.value = true;

    const apiMap = {
      [AccountTypes.MYSQL]: getMysqlPermissionRules,
      [AccountTypes.TENDBCLUSTER]: getMysqlPermissionRules,
      [AccountTypes.MONGODB]: getMongodbPermissionRules,
      [AccountTypes.SQLSERVER]: getSqlserverPermissionRules,
    };

    apiMap[props.accountType]({
      offset: 0,
      limit: -1,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      account_type: props.accountType,
    })
      .then((res) => {
        emits('success', res.results);
        accountRules.value = res.results;
        // // 只有一个则直接默认选中
        // if (curRules.value.length === 1) {
        //   // accessDbs.value = [curRules.value[0].access_db];
        //   emits('success', [curRules.value[0].access_db]);
        // }
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  getAccount();
</script>
