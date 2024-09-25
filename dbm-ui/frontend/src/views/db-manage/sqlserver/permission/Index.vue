<template>
  <div class="sqlserver-permission-rules">
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
    <div class="operation-box">
      <AuthButton
        action-id="sqlserver_account_create"
        theme="primary"
        @click="accountDialogIsShow = true">
        {{ t('新建账号') }}
      </AuthButton>
      <DbSearchSelect
        v-model="tableSearch"
        :data="filters"
        :placeholder="t('账号名称_DB名称_权限名称')"
        style="width: 500px"
        unique-select
        @change="handleSearch" />
    </div>
    <DbTable
      ref="tableRef"
      class="rules-table"
      :columns="columns"
      :data-source="getSqlserverPermissionRules"
      releate-url-query
      :row-class="setRowClass"
      row-hover="auto"
      @clear-search="handleClearSearch"
      @refresh="fetchData" />
  </div>
  <!-- 创建账户 -->
  <AccountDialog
    v-model="accountDialogIsShow"
    @success="fetchData" />
  <!-- 账号信息 dialog -->
  <BkDialog
    v-model:is-show="accountInformationShow"
    dialog-type="show"
    :draggable="false"
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
    :db-operations="dbOperations"
    @success="fetchData" />
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :permisson-rule-list="selectedList" />
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlserverPermissionAccountModel from '@services/model/sqlserver/sqlserver-permission-account';
  import {
    deleteSqlserverAccount,
    getSqlserverPermissionRules,
  } from '@services/source/sqlserverPermissionAccount';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/ClusterAuthorize.vue';

  import { getSearchSelectorParams , messageSuccess } from '@utils';

  import AccountDialog from './components/AccountDialog.vue';
  import CreateRuleSlider from './components/CreateRule.vue';

  const { t } = useI18n();

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => (
        <TextOverflowLayout>
          {{
            prepend: () => data.rules.length > 1 && (
              <div
                class="row-expand-btn"
                onClick={() => handleToggleExpand(data)}>
                <db-icon
                  type="down-shape"
                  class={{
                    'expand-flag': true,
                    'is-expand': !rowExpandMap.value[data.account.account_id],
                  }} />
              </div>
            ),
            default: () => (
              <bk-button
                text
                theme="primary"
                onClick={() => handleViewAccount(data)}>
                {data.account.user}
              </bk-button>
            ),
            append: () => (
              <>
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
                  class="add-rule-btn"
                  size="small"
                  onClick={() => handleShowCreateRule(data)}>
                  {t('新建规则')}
                </bk-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('访问的DB名'),
      field: 'access_db',
      render: ({ data }: { data: SqlserverPermissionAccountModel }) => {
        if (!data.rules.length) {
          return (
            <div class="cell-row">
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
            <div class="cell-row">
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
            class="cell-row"
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
          <div class="cell-row">
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
            <div class="cell-row">
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

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const accountInformationData = ref();
  const accountInformationShow = ref(false);
  const ruleShow = ref(false);
  const ruleAccountId = ref();
  // const accountMapList = ref<SqlserverPermissionAccountModel['account'][]>([]);
  const tableSearch = ref([]);
  const accountDialogIsShow = ref(false);
  const authorizeShow = ref(false);
  const rowExpandMap = shallowRef<Record<number, boolean>>({});
  const selectedList = shallowRef<SqlserverPermissionAccountModel[]>([]);

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
      logical: '&',
      children: [...dbOperations, 'db_owner'].map((id: string) => ({
        id: id.toLowerCase(),
        name: id,
      })),
    },
  ]);

  // const {
  //   data: sqlserverPermissionRulesData,
  //   loading: isLoading,
  //   run: runAccountRulesList,
  // } = useRequest(getSqlserverPermissionRules, {
  //   manual: true,
  //   onSuccess(sqlserverPermissionRules) {
  //     accountMapList.value = sqlserverPermissionRules.results.map(item => item.account);
  //   },
  // });

  const { run: runDeleteAccount } = useRequest(deleteSqlserverAccount, {
    manual: true,
    onSuccess() {
      messageSuccess(t('成功删除账号'));
      accountInformationShow.value = false;
      fetchData();
    },
  });

  const fetchData = () => {
    tableRef.value!.fetchData(
      {
        ...getSearchSelectorParams(tableSearch.value),
      },
      {
        account_type: AccountTypes.SQLSERVER,
      }
    )
  }

  const handleSearch = () => {
    fetchData();
  };

  const handleClearSearch = () => {
    tableSearch.value = [];
    fetchData();
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
    InfoBox({
      type: 'warning',
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
    rule: SqlserverPermissionAccountModel['rules'][number],
  ) => {
    authorizeShow.value = true;
    selectedList.value = [
      Object.assign({}, data, { rules: [rule] }),
    ];
  };

  onMounted(() => {
    fetchData()
  })
</script>

<style lang="less" scoped>
  .sqlserver-permission-rules {
    .permission-info-alert {
      margin-bottom: 16px;

      .label {
        font-weight: 700;
      }
    }

    .operation-box {
      display: flex;
      padding-bottom: 16px;
      justify-content: space-between;
      align-items: center;
    }

    :deep(.db-table) {
      .rules-table {
        .cell {
          padding: 0 !important;
        }

        tr {
          &:hover {
            .add-rule-btn {
              display: inline-flex;
              margin-left: 8px;
            }
          }

          &.is-new {
            td {
              background-color: #f3fcf5 !important;
            }
          }
        }

        th {
          padding: 0 16px;
        }

        td {
          &:first-child {
            padding: 0 16px;
          }
        }

        .cell-row {
          height: calc(var(--row-height) - 4px);
          padding: 0 16px;
          overflow: hidden;
          line-height: calc(var(--row-height) - 4px);
          text-overflow: ellipsis;
          white-space: nowrap;

          & ~ .cell-row {
            border-top: 1px solid #dcdee5;
          }
        }

        .row-expand-btn {
          display: flex;
          padding-right: 8px;
          cursor: pointer;
          align-items: center;
          justify-content: center;

          .expand-flag {
            transform: rotate(-90deg);
            transition: all 0.1s;

            &.is-expand {
              transform: rotate(0);
            }
          }
        }

        .add-rule-btn {
          display: none;
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
