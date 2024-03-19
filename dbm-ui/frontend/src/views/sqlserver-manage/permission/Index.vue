<template>
  <div class="permission-rules">
    <BkAlert
      class="permission-info-alert"
      closable
      theme="info">
      <template #title>
        <p>
          <span class="label">{{ t('账号') }} ：</span>
          {{ t('访问 DB 的用户名，包括它的密码') }}
        </p>
        <p>
          <span class="label">{{ t('授权规则') }} ：</span>
          {{ t('权限模板，预定义账号拥有哪些权限') }}
        </p>
        <p>
          <span class="label">{{ t('授权') }} ：</span>
          {{ t('根据 grant 语法授予 DB 实例的访问权限') }}
        </p>
      </template>
    </BkAlert>
    <div class="permission-rules-operations">
      <BkButton
        theme="primary"
        @click="accountDialogIsShow = true">
        {{ t('新建账号') }}
      </BkButton>
      <DbSearchSelect
        v-model="searchData"
        :data="filters"
        :placeholder="t('账号名称_DB名称_权限名称')"
        style="width: 500px"
        unique-select
        @change="handleSearch" />
    </div>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        class="permission-rules-table"
        :columns="columns"
        :data="sqlserverPermissionRulesData?.results || []"
        :max-height="tableMaxHeight"
        :row-class="setRowClass"
        @refresh="fetchAccountRuleList" />
    </BkLoading>
  </div>
  <!-- 创建账户 -->
  <AccountDialog
    v-model="accountDialogIsShow"
    @success="fetchAccountRuleList" />
  <!-- 账号信息 dialog -->
  <BkDialog
    v-model:is-show="accountInformationShow"
    dialog-type="show"
    :draggable="false"
    height="auto"
    quick-close
    :title="t('账号信息')"
    :width="480">
    <div class="account-details">
      <div
        v-for="column of accountColumns"
        :key="column.key"
        class="account-details-item">
        <span class="account-details-label">{{ column.label }}：</span>
        <span class="account-details-value">
          {{ column.value ?? accountInformationData.account[column.key] ?? accountInformationData[column.key] }}
        </span>
      </div>
      <div
        v-if="accountInformationData.rules?.length === 0"
        class="account-details-item">
        <span class="account-details-label" />
        <span class="account-details-value">
          <BkButton
            hover-theme="danger"
            @click="handleDeleteAccount(accountInformationData)">
            {{ t('删除账号') }}
          </BkButton>
        </span>
      </div>
    </div>
  </BkDialog>
  <!-- 添加授权规则 -->
  <CreateRuleSlider
    v-model="ruleShow"
    :account-id="ruleAccountId"
    :account-map-list="accountMapList"
    :db-operations="dbOperations"
    @success="fetchAccountRuleList" />
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :access-dbs="authorizeDbs"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.SQLSERVER_HA]"
    :user="authorizeUser" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlserverPermissionAccountModel from '@services/model/sqlserver-permission/sqlserver-permission-account';
  import {
    deleteSqlserverAccount,
    getSqlserverPermissionRules,
  } from '@services/source/sqlserverPermissionAccount';

  import {
    useInfoWithIcon,
    useTableMaxHeight,
  } from '@hooks';

  import { AccountTypes, ClusterTypes, OccupiedInnerHeight } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { getSearchSelectorParams , messageSuccess } from '@utils';

  import AccountDialog from './components/AccountDialog.vue';
  import CreateRuleSlider from './components/CreateRule.vue';

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => (
        <div
          class="permission-rules-cell"
          onClick={ () => handleToggleExpand(data) }>
            {
              data.rules.length > 1 && (
                <Db-Icon
                  type='down-shape'
                  class={ ['user-icon', { 'user-icon-expand': !rowExpandMap.value[data.account.account_id] }] } />
              )
            }
            <div class="user-name">
              <bk-button
                text
                theme="primary"
                class="user-name-text"
                onClick={() => handleViewAccount(data)}>
                  {data.account.user}
              </bk-button>
              {
                data.isNew && (
                  <bk-tag
                    size="small"
                    theme="success"
                    class="ml-4">
                    NEW
                  </bk-tag>
                )
              }
              <bk-button
                class="add-rule ml-8"
                size="small"
                onClick={() => handleShowCreateRule(data)}>
                 {t('新建规则')}
              </bk-button>
            </div>
        </div>
      ),
    },
    {
      label: t('访问的DB名'),
      field: 'access_db',
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => {
        if (!data.rules.length) {
          return (
            <div class="permission-rules-cell">
              <span>{ t('暂无规则') }，</span>
              <bk-button
                 theme="primary"
                 size="small"
                 text
                 onClick={ () => handleShowCreateRule(data) }>
                  { t('立即新建') }
              </bk-button>
            </div>
          );
        }
        return (
          getRenderList(data).map(rule => (
            <div class="permission-rules-cell">
              <bk-tag>{ rule.access_db || '--' }</bk-tag>
            </div>
          ))
        );
      },
    },
    {
      label: t('权限'),
      field: 'privilege',
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => (
        getRenderList(data).map(rule => (
          <div
            class="permission-rules-cell"
            v-overflow-tips>
              { (rule.privilege && rule.privilege.replace(/,/g, '，')) || '--' }
          </div>
        ))
      ),
    },
    {
      label: t('操作'),
      width: 140,
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => {
        if (data.rules.length === 0) {
          return (
          <div class="permission-rules-cell">
            <bk-button
              theme="primary"
              text
              onClick={ () => handleDeleteAccount(data) }>
                {t('删除账号')}
            </bk-button>
          </div>
          );
        }

        return (
          getRenderList(data).map(item => (
            <div class="permission-rules-cell">
              <bk-button
                theme="primary"
                text
                onClick={ () => handleShowAuthorize(data, item) }>
                  { t('授权') }
              </bk-button>
            </div>
          ))
        );
      },
    },
  ];

  const accountColumns: Array<{
    label: string,
    key: keyof SqlserverPermissionAccountModel['account'] | 'createAtDisplay'
    value?: string
  }> = [
    {
      label: t('账号名'),
      key: 'user',
    },
    {
      label: t('密码'),
      key: 'password',
      value: '****************',
    },
    {
      label: t('创建时间'),
      key: 'createAtDisplay',
    },
    {
      label: t('创建人'),
      key: 'creator',
    },
  ];

  const dbOperations = ['db_datawriter', 'db_datareader'];

  const accountInformationData = ref();
  const accountInformationShow = ref(false);
  const ruleShow = ref(false);
  const ruleAccountId = ref();
  const accountMapList = ref<SqlserverPermissionAccountModel['account'][]>([]);
  const searchData = ref([]);
  const accountDialogIsShow = ref(false);
  const authorizeShow = ref(false);
  const authorizeUser = ref();
  const authorizeDbs = ref();
  const rowExpandMap = shallowRef<Record<number, boolean>>({});

  /**
   * search select 过滤参数
   */
  const filters = computed(() => [
    {
      name: t('账号名称'),
      id: 'user',
    },
    {
      name: t('DB名称'),
      id: 'access_db',
    },
    {
      name: t('权限'),
      id: 'privilege',
      multiple: true,
      children: [...dbOperations, 'db_owner'].map((id: string) => ({
        id: id.toLowerCase(),
        name: id,
      })),
    },
  ]);

  const {
    data: sqlserverPermissionRulesData,
    loading: isLoading,
    run: runAccountRulesList,
  } = useRequest(getSqlserverPermissionRules, {
    manual: true,
    onSuccess(sqlserverPermissionRules) {
      accountMapList.value = sqlserverPermissionRules.results.map(item => item.account);
    },
  });

  const { run: runDeleteAccount } = useRequest(deleteSqlserverAccount, {
    manual: true,
    onSuccess() {
      messageSuccess(t('成功删除账号'));
      accountInformationShow.value = false;
      fetchAccountRuleList();
    },
  });

  const fetchAccountRuleList = () => {
    runAccountRulesList({
      ...getSearchSelectorParams(searchData.value),
      account_type: AccountTypes.SQLSERVER
    });
  }
  fetchAccountRuleList()

  const handleSearch = () => {
    fetchAccountRuleList();
  };

  // 设置行样式
  const setRowClass = (row: SqlserverPermissionAccountModel) => (row.isNew ? 'is-new' : '');

  /**
   * 列表项展开/收起
   */
  const handleToggleExpand = (data: SqlserverPermissionAccountModel) => {
    if (data.rules.length <= 1) {
      return;
    }
    const expandMap = { ...rowExpandMap.value };
    expandMap[data.account.account_id] = !expandMap[data.account.account_id];
    rowExpandMap.value = expandMap;
  };

  const handleDeleteAccount = (data: SqlserverPermissionAccountModel) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: data.account.user }),
      onConfirm: async () => {
        runDeleteAccount({
          account_id: data.account.account_id,
          account_type: AccountTypes.SQLSERVER
        });
        return true;
      },
    });
  };

  /**
   * 展开/收起渲染列表
   */
  const getRenderList = (data: SqlserverPermissionAccountModel) => (!rowExpandMap.value[data.account.account_id]
    ? data.rules : data.rules.slice(0, 1));

  const handleViewAccount = (data: SqlserverPermissionAccountModel) => {
    accountInformationData.value = data;
    accountInformationShow.value = true;
  };

  const handleShowCreateRule = (data: SqlserverPermissionAccountModel) => {
    ruleAccountId.value = data.account.account_id;
    ruleShow.value = true;
  };

  const handleShowAuthorize = (
    data: SqlserverPermissionAccountModel,
    item: SqlserverPermissionAccountModel['rules'][number],
  ) => {
    authorizeShow.value = true;
    authorizeUser.value = data.account.user;
    authorizeDbs.value = [item.access_db];
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .permission-rules {
    .permission-info-alert {
      margin-bottom: 16px;

      :deep(.label) {
        font-weight: 700;
      }
    }

    .permission-rules-operations {
      justify-content: space-between;
      padding-bottom: 16px;
      .flex-center();
    }

    :deep(.user-name) {
      height: 100%;
      padding-left: 24px;
      cursor: pointer;
      align-items: center;
      .flex-center();

      .user-name-text {
        font-weight: bold;
      }

      .add-rule {
        display: none;
      }
    }

    :deep(.permission-rules-cell) {
      position: relative;
      padding: 0 15px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      border-bottom: 1px solid @border-disable;

      &:last-child {
        border-bottom: 0;
      }
    }

    :deep(.user-icon) {
      position: absolute;
      top: 50%;
      left: 15px;
      transform: translateY(-50%) rotate(-90deg);
      transition: all 0.2s;
    }

    :deep(.user-icon-expand) {
      transform: translateY(-50%) rotate(0);
    }

    .permission-rules-table {
      transition: all 0.5s;

      :deep(.bk-table-body table tbody tr) {
        &:hover {
          .add-rule {
            display: flex;
          }
        }

        &.is-new {
          td {
            background-color: #f3fcf5 !important;
          }
        }

        td {
          .cell {
            padding: 0 !important;
          }

          &:first-child {
            .cell,
            .permission-rules-cell {
              height: 100% !important;
            }
          }
        }
      }
    }
  }

  .account-details {
    font-size: @font-size-mini;

    .account-details-item {
      display: flex;
      padding-bottom: 16px;
    }

    .account-details-label {
      width: 90px;
      text-align: right;
      flex-shrink: 0;
    }

    .account-details-value {
      color: @title-color;
    }
  }
</style>
