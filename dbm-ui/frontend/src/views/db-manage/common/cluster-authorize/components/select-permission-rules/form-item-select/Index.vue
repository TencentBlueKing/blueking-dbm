<template>
  <h5 class="cluster-authorize-bold cluster-authorize-label pb-16">
    {{ t('权限规则') }}
  </h5>
  <BkFormItem
    :label="t('账号名')"
    property="user"
    required>
    <BkSelect
      v-model="user"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="accountState.isLoading">
      <BkOption
        v-for="item of accountState.rules"
        :key="item.account.account_id"
        :label="item.account.user"
        :value="item.account.user" />
    </BkSelect>
  </BkFormItem>
  <BkFormItem
    :label="t('访问DB')"
    property="access_dbs"
    required>
    <BkSelect
      v-model="accessDbs"
      :clearable="false"
      collapse-tags
      filterable
      :input-search="false"
      :loading="accountState.isLoading"
      multiple
      multiple-mode="tag"
      show-select-all>
      <BkOption
        v-for="item of curRules"
        :key="item.rule_id"
        :label="item.access_db"
        :value="item.access_db" />
      <template #extension>
        <BkButton
          class="to-create-rules"
          text
          @click="handleToCreateRules">
          <DbIcon
            class="mr-4"
            type="plus-circle" />
          {{ t('跳转新建规则') }}
        </BkButton>
      </template>
    </BkSelect>
  </BkFormItem>
  <BkFormItem
    v-model="rules"
    :label="t('权限明细')">
    <BkAlert
      class="mb-16 mt-10"
      theme="warning"
      :title="t('注意_对从域名授权时仅会授予 select 权限')" />
    <DbOriginalTable
      :columns="permissonColumns"
      :data="rules"
      :empty-text="t('请选择访问DB')" />
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

  const props = defineProps<Props>();

  const user = defineModel<string>('user', {
    default: '',
  });

  const accessDbs = defineModel<string[]>('accessDbs', {
    default: () => [],
  });

  const rules = defineModel<PermissionRule['rules']>('rules', {
    default: () => [],
  });

  const router = useRouter();
  const { t } = useI18n();

  /** 权限规则功能 */
  const accountState = reactive({
    isLoading: false,
    rules: [] as PermissionRule[],
  });

  const curRules = computed(() => {
    if (user.value === '') {
      return [];
    }

    const item = accountState.rules.find((item) => item.account.user === user.value);
    return item?.rules || [];
  });

  const permissonColumns = [
    {
      label: 'DB',
      field: 'access_db',
      showOverflowTooltip: true,
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => {
        if (!cell) {
          return '--';
        }
        return cell.replace(/,/g, ', ');
      },
    },
  ];

  const updateRules = () => {
    if (accessDbs.value.length === 0) {
      rules.value = [];
      return;
    }
    rules.value = curRules.value.filter((item) => accessDbs.value.includes(item.access_db));
  };

  watch(curRules, updateRules, {
    immediate: true,
  });

  watch(accessDbs, updateRules);

  /**
   * 跳转新建规则界面
   */
  const handleToCreateRules = () => {
    const routeMap = {
      [AccountTypes.MYSQL]: 'PermissionRules',
      [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
      [AccountTypes.MONGODB]: 'MongodbPermission',
      [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules',
    };
    const url = router.resolve({ name: routeMap[props.accountType] });
    window.open(url.href, '_blank');
  };

  /**
   * 获取账号信息
   */
  const getAccount = () => {
    accountState.isLoading = true;

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
        accountState.rules = res.results;
        // 只有一个则直接默认选中
        if (curRules.value.length === 1) {
          accessDbs.value = [curRules.value[0].access_db];
        }
      })
      .finally(() => {
        accountState.isLoading = false;
      });
  };

  getAccount();
</script>

<style lang="less" scoped>
  .to-create-rules {
    display: inline-block;
    margin-left: 16px;
    line-height: 40px;

    i {
      color: @gray-color;
    }

    &:hover {
      color: @primary-color;

      i {
        color: @primary-color;
      }
    }
  }
</style>
