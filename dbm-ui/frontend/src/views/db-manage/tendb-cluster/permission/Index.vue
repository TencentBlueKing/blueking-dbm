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
  <PermissionCatch>
    <div class="permission-rules-page">
      <div class="permission-operations">
        <AuthButton
          action-id="tendbcluster_account_create"
          theme="primary"
          @click="handleAddAcount">
          {{ t('新建账号') }}
        </AuthButton>
        <DbSearchSelect
          v-model="tableSearch"
          :data="filters"
          :placeholder="t('请输入账号名称/DB名称/权限名称')"
          style="width: 500px"
          unique-select
          @change="fetchData" />
      </div>
      <DbTable
        ref="tableRef"
        class="rules-table"
        :columns="columns"
        :data-source="getPermissionRules"
        releate-url-query
        :row-class="setRowClass"
        row-hover="auto"
        show-overflow-tooltip
        @clear-search="handleClearSearch" />
      <AddAccountDialog
        v-model="addAccountDialogShow"
        @success="fetchData" />
      <AccountInfoDialog
        v-model="accountInfoDialogShow"
        :info="accountInfoDialogInfo"
        @delete-account="handleDeleteAccountSuccess" />
      <CreateRule
        v-model="createRuleShow"
        :account-id="createRuleAccountId"
        :rule-obj="currentRule"
        @success="fetchData" />
      <ClusterAuthorize
        ref="clusterAuthorizeRef"
        v-model="authorizeShow"
        :access-dbs="authorizeDbs"
        :account-type="AccountTypes.TENDBCLUSTER"
        :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
        :user="authorizeUser" />
    </div>
  </PermissionCatch>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/permission';
  import type { PermissionRuleInfo } from '@services/types/permission';

  import { useTicketCloneInfo, } from '@hooks';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import PermissionCatch from '@components/apply-permission/Catch.vue'
  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/ClusterAuthorize.vue';

  import { getSearchSelectorParams } from '@utils';

  import { dbOperations } from './common/consts';
  import AccountInfoDialog from './components/AccountInfoDialog.vue';
  import AddAccountDialog from './components/AddAccountDialog.vue';
  import CreateRule from './components/CreateRule.vue';
  import { useDeleteAccount } from './hooks/useDeleteAccount';

  const { t } = useI18n();

  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    onSuccess(cloneData) {
      const {
        dbs,
        user,
        clusterType,
        clusterList,
        sourceIpList,
      } = cloneData;
      authorizeShow.value = true;
      authorizeDbs.value = dbs;
      authorizeUser.value = user;
      clusterAuthorizeRef.value!.initSelectorData({
        clusterType,
        clusterList,
        sourceIpList,
      });
      window.changeConfirm = true;
    },
  });

  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    onSuccess(cloneData) {
      const {
        dbs,
        user,
        clusterType,
        clusterList,
        sourceIpList,
      } = cloneData;
      authorizeShow.value = true;
      authorizeDbs.value = dbs;
      authorizeUser.value = user;
      clusterAuthorizeRef.value!.initSelectorData({
        clusterType,
        clusterList,
        sourceIpList,
      });
      window.changeConfirm = true;
    },
  });

  const setRowClass = (row: MysqlPermissonAccountModel) => (row.isNew ? 'is-new' : '');

  const { deleteAccountReq } = useDeleteAccount();

  const clusterAuthorizeRef = ref<InstanceType<typeof ClusterAuthorize>>();
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tableSearch = ref([]);
  const currentRule = ref({} as MysqlPermissonAccountModel['rules'][number])

  const rowExpandMap = shallowRef<Record<number, boolean>>({});

  const fetchData = () => {
    tableRef.value!.fetchData(
      {
        ...getSearchSelectorParams(tableSearch.value),
      },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        account_type: AccountTypes.TENDBCLUSTER,
      }
    )
  };

  const filters = [
    {
      name: t('账号名称'),
      id: 'user',
    },
    {
      name: t('访问DB'),
      id: 'access_db',
    },
    {
      name: t('权限'),
      id: 'privilege',
      multiple: true,
      logical: '&',
      children: [
        ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.glob.map(id => ({ id, name: id })),
      ],
    },
  ];

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
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
                onClick={(event: MouseEvent) => handleViewAccount(data, event)}>
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
                <auth-button
                  class="add-rule-btn"
                  size="small"
                  action-id="tendbcluster_add_account_rule"
                  permission={data.permission.tendbcluster_add_account_rule}
                  resource={data.account.account_id}
                  onClick={ (event: Event) => handleShowCreateRule(data, event) }>
                  { t('添加授权规则') }
                </auth-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('访问DB'),
      field: 'access_db',
      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <span>{ t('暂无规则') }，</span>
              <auth-button
                theme="primary"
                size="small"
                text
                action-id="tendbcluster_add_account_rule"
                permission={data.permission.tendbcluster_add_account_rule}
                resource={data.account.account_id}
                onClick={ (event: Event) => handleShowCreateRule(data, event) }>
                { t('立即新建') }
              </auth-button>
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
      showOverflowTooltip: false,
      sort: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
        getRenderList(data).map((rule) => {
          const { privilege } = rule;

          return (
            <div class="cell-row" v-overflow-tips>
              {
                !privilege ? '--' : privilege.replace(/,/g, '，')
              }
            </div>
          );
        })
      ),
    },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <auth-button
                action-id="tendbcluster_account_delete"
                permission={data.permission.tendbcluster_account_delete}
                resource={data.account.account_id}
                theme="primary"
                text
                onClick={ () => handleDeleteAccount(data) }>
                { t('删除账号') }
              </auth-button>
            </div>
          );
        }

        return (
          getRenderList(data).map((item, index) => (
            <div class="cell-row">
              <bk-button
                theme="primary"
                text
                onClick={ () => handleShowAuthorize(data, item) }>
                { t('授权') }
              </bk-button>
              <bk-button
                theme="primary"
                class="ml-8"
                text
                onClick={(event: PointerEvent) => handleShowEditRule(event, data, index)}>
                {t('编辑')}
              </bk-button>
            </div>
          ))
        );
      },
    },
  ];

  const handleClearSearch = () => {
    tableSearch.value = [];
    fetchData();
  };

  /**
   * 展开/收起渲染列表
   */
  const getRenderList = (data: MysqlPermissonAccountModel) => (!rowExpandMap.value[data.account.account_id]
    ? data.rules : data.rules.slice(0, 1));

  const handleToggleExpand = (data: MysqlPermissonAccountModel) => {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) {
      return;
    }
    const expandMap = { ...rowExpandMap.value };
    expandMap[data.account.account_id] = !expandMap[data.account.account_id];
    rowExpandMap.value = expandMap;
  };

  const addAccountDialogShow = ref(false);
  const accountInfoDialogShow = ref(false);
  const accountInfoDialogInfo = ref({} as MysqlPermissonAccountModel);

  const handleAddAcount = () => {
    addAccountDialogShow.value = true;
  };

  const handleViewAccount = (data: MysqlPermissonAccountModel, event: Event) => {
    event.stopPropagation();

    accountInfoDialogShow.value = true;
    accountInfoDialogInfo.value = data;
  };

  const handleDeleteAccountSuccess = () => {
    accountInfoDialogShow.value = false;
    fetchData();
  };

  const createRuleShow = ref(false);
  const createRuleAccountId = ref(-1);

  const handleShowCreateRule = (row: MysqlPermissonAccountModel, event: Event) => {
    event.stopPropagation();
    currentRule.value = {} as MysqlPermissonAccountModel['rules'][number];
    createRuleAccountId.value = row.account.account_id;
    createRuleShow.value = true;
  };

  const handleShowEditRule = (e: PointerEvent, row: MysqlPermissonAccountModel, index: number) => {
    e.stopPropagation();
    createRuleAccountId.value = row.account.account_id;
    currentRule.value = row.rules[index];
    createRuleShow.value = true;
  };

  const handleDeleteAccount = (data: MysqlPermissonAccountModel) => {
    const { user, account_id: accountId } = data.account;

    deleteAccountReq(user, accountId, handleDeleteAccountSuccess);
  };

  const authorizeShow = ref(false);
  const authorizeUser = ref('');
  const authorizeDbs = ref<string []>([]);

  const handleShowAuthorize = (row: MysqlPermissonAccountModel, rule: PermissionRuleInfo) => {
    authorizeShow.value = true;
    authorizeUser.value = row.account.user;
    authorizeDbs.value = [rule.access_db];
  };

  // onMounted(() => {
  //   fetchData()
  // })
</script>

<style lang="less" scoped>
  .permission-rules-page {
    .permission-operations {
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
</style>
