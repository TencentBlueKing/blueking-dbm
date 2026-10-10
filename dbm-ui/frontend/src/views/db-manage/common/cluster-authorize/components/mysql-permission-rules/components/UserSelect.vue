<template>
  <BkFormItem
    :label="t('账号名')"
    property="user"
    required>
    <DbSelect
      ref="selectRef"
      v-model="user"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      :remote-method="handleSearchAccount"
      :scroll-loading="isLoading"
      @scroll-end="handleLoadMore"
      @toggle="handleToggleSelect">
      <DbOption
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
    </DbSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import type { RouteLocationRaw } from 'vue-router';

  import { getPermissionRules as getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { getPermissionRules as getMysqlPermissionRules } from '@services/source/mysqlPermissionAccount';
  import { getPermissionRules as getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import type { PermissionRule, PermissionRulesResult } from '@services/types';

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

  const selectRef = useTemplateRef('selectRef');
  const accounts = ref<PermissionRule[]>([]);

  /**
   * 账号类型对应的账号规则查询接口
   */
  const apiMap = {
    [AccountTypes.MONGODB]: getMongodbPermissionRules,
    [AccountTypes.MYSQL]: getMysqlPermissionRules,
    [AccountTypes.SQLSERVER]: getSqlserverPermissionRules,
    [AccountTypes.TENDBCLUSTER]: getMysqlPermissionRules,
  };

  /**
   * 各账号类型的返回结构一致，统一收敛成账号规则列表
   */
  const queryPermissionRules = async (
    params: Parameters<typeof getMysqlPermissionRules>[0],
  ): Promise<PermissionRulesResult> => {
    const result = await apiMap[props.accountType](params);
    return result;
  };

  const updateAccoutRules = () => {
    emits('change', accounts.value.find((item) => item.account.user === user.value)?.rules || []);
  };

  watch(user, updateAccoutRules);

  /**
   * 账号下拉懒加载：分页拉取账号规则聚合出的账号，避免全量请求
   */
  const PAGE_SIZE = 20;
  const pagination = reactive({
    count: 0,
    offset: 0,
  });
  let searchKeyword = '';

  const { loading: isLoading, run: getPermissionRulesRun } = useRequest(queryPermissionRules, {
    manual: true,
    onSuccess({ count, results }, [params]) {
      // 过期响应直接丢弃：请求发起时的关键字 / offset 与当前状态任一不一致即视为过期
      if ((params.user || '') !== searchKeyword || params.offset !== pagination.offset) {
        return;
      }
      pagination.count = count;
      accounts.value = _.uniqBy([...accounts.value, ...results], (item) => item.account.account_id);
    },
  });

  const fetchAccounts = (offset: number) => {
    getPermissionRulesRun({
      account_type: props.accountType,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      limit: PAGE_SIZE,
      offset,
      ...(searchKeyword ? { user: searchKeyword } : {}),
    });
  };

  /**
   * 远程搜索账号名（带防抖）
   */
  const handleSearchAccount = _.debounce((keyword: string) => {
    searchKeyword = keyword.trim();
    pagination.offset = 0;
    pagination.count = 0;
    // 搜索重置已加载列表，仅保留当前已选账号（懒加载下回显需要）
    accounts.value = accounts.value.filter((item) => item.account.user === user.value);
    fetchAccounts(0);
  }, 300);

  /**
   * 触底加载下一页
   */
  const handleLoadMore = () => {
    if (isLoading.value || pagination.offset + PAGE_SIZE >= pagination.count) {
      return;
    }
    pagination.offset += PAGE_SIZE;
    fetchAccounts(pagination.offset);
  };

  /**
   * 下拉内容不足以滚动时自动续拉下一页
   * （后端按规则条数分页、前端按账号展示，一页可能聚合不出足够撑满可视区的账号数；
   * 由 isLoading 的 watch 在每次请求结束后再次触发，形成链式填充直至可滚动或数据加载完）
   */
  const autoFillIfNotScrollable = () => {
    // 下拉未展开时无需处理
    if (!selectRef.value?.isPopoverShow) {
      return;
    }
    const dropdownEl = selectRef.value?.contentRef?.querySelector('.dbm-select-dropdown');
    // 可滚动即达标；数据加载完则停止
    if (!dropdownEl || dropdownEl.scrollHeight > dropdownEl.clientHeight || pagination.offset + PAGE_SIZE >= pagination.count) {
      return;
    }
    handleLoadMore();
  };

  watch(isLoading, (loading) => {
    if (!loading) {
      // 渲染完成后再测量
      nextTick(autoFillIfNotScrollable);
    }
  });

  /**
   * 下拉展开时启动自动续拉检测
   */
  const handleToggleSelect = (isShow: boolean) => {
    if (isShow) {
      nextTick(autoFillIfNotScrollable);
    }
  };

  /**
   * 入口带入账号名时（从授权规则行发起授权），懒加载列表里可能不含该账号，
   * 单独按账号名取一次，保证权限明细能正常回显
   */
  const { run: getSelectedAccountRun } = useRequest(queryPermissionRules, {
    manual: true,
    onSuccess({ results }) {
      const matchedAccount = results.find((item) => item.account.user === user.value);
      if (!matchedAccount) {
        return;
      }
      if (!accounts.value.some((item) => item.account.account_id === matchedAccount.account.account_id)) {
        accounts.value.unshift(matchedAccount);
      }
      updateAccoutRules();
    },
  });

  watch(
    user,
    (userName) => {
      // 已加载的账号无需重复拉取
      if (!userName || accounts.value.some((item) => item.account.user === userName)) {
        return;
      }
      getSelectedAccountRun({
        account_type: props.accountType,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        limit: -1,
        offset: 0,
        user: userName,
      });
    },
    { immediate: true },
  );

  fetchAccounts(0);

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
    margin-left: 10px;
    font-family: MicrosoftYaHei, Arial, sans-serif;
    color: #4d4f56;
    cursor: pointer;

    .add-account-icon {
      margin-right: 5px;
      font-size: 14px;
      color: #979ba5;
    }
  }
</style>
