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
  <div class="permission">
    <div class="permission-operations">
      <BkButton
        theme="primary"
        @click="handleAddAcount">
        {{ t('新建账号') }}
      </BkButton>
      <DbSearchSelect
        v-model="tableSearch"
        :data="filters"
        :placeholder="t('请输入账号名称/DB名称/权限名称')"
        style="width: 500px;"
        unique-select
        @change="getList" />
    </div>
    <BkLoading :loading="tableIsLoading">
      <DbOriginalTable
        class="permission-table"
        :columns="columns"
        :data="tableData"
        :is-anomalies="tableIsAnomalies"
        :is-searching="tableSearch.length > 0"
        :max-height="tableMaxHeight"
        :row-class="setRowClass"
        row-hover="auto"
        show-overflow-tooltip
        @clear-search="handleClearSearch" />
    </BkLoading>
    <AddAccountDialog
      v-model="addAccountDialogShow"
      @success="getList" />
    <AccountInfoDialog
      v-model="accountInfoDialogShow"
      :info="accountInfoDialogInfo"
      @delete-account="handleDeleteAccountSuccess" />
    <CreateRule
      v-model="createRuleShow"
      :account-id="createRuleAccountId"
      @success="getList" />
    <ClusterAuthorize
      v-model="authorizeShow"
      :access-dbs="authorizeDbs"
      :account-type="AccountTypes.TENDBCLUSTER"
      :cluster-type="ClusterTypes.TENDBCLUSTER"
      :tab-list="[ClusterTypes.TENDBCLUSTER]"
      :user="authorizeUser" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  // TODO INTERFACE
  import { getPermissionRules } from '@services/permission';
  import type { PermissionRuleInfo } from '@services/types/permission';

  import { useTableMaxHeight } from '@hooks';

  import {
    AccountTypes,
    ClusterTypes,
    OccupiedInnerHeight,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { getSearchSelectorParams } from '@utils';

  import { dbOperations } from './common/consts';
  import type { PermissionTableRow } from './common/types';
  import {
    getRenderList,
    isNewUser,
  } from './common/utils';
  import AccountInfoDialog from './components/AccountInfoDialog.vue';
  import AddAccountDialog from './components/AddAccountDialog.vue';
  import CreateRule from './components/CreateRule.vue';
  import { useDeleteAccount } from './hooks/useDeleteAccount';

  import { useGlobalBizs } from '@/stores';

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);
  const setRowClass = (row: PermissionTableRow) => (isNewUser(row) ? 'is-new' : '');

  const { deleteAccountReq } = useDeleteAccount();

  const tableIsAnomalies = ref(false);
  const tableSearch = ref([]);

  const {
    run: getPermissionRulesRun,
    loading: tableIsLoading,
    data: tableList,
  } = useRequest(getPermissionRules, {
    manual: false,
    onSuccess() {
      tableIsAnomalies.value = false;
    },
    onError() {
      tableIsAnomalies.value = true;
    },
  });

  const tableData = ref([] as PermissionTableRow[]);

  watch(tableList, () => {
    tableData.value = tableList.value?.results.map((item => ({ isExpand: true, ...item }))) || [];
  });

  const getList = () => {
    getPermissionRulesRun({
      ...getSearchSelectorParams(tableSearch.value),
      account_type: AccountTypes.TENDBCLUSTER,
      bk_biz_id: currentBizId,
    });
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
      render: ({ data }: { data: PermissionTableRow }) => (
        <div class="permission-cell" onClick={ handleToggleExpand.bind(null, data) }>
          {
            data.rules.length > 1
              ? <db-icon
                  type="down-shape"
                  class={['user-icon', {
                    'user-icon-expand': data.isExpand,
                  }]} />
              : null
          }
          <div class="user-name">
            <bk-button
              text
              theme="primary"
              class="user-name-text text-overflow"
              onClick={ (event: Event) => handleViewAccount(data, event) }>
              { data.account.user }
            </bk-button>
            {
              isNewUser(data)
              ? <span class="glob-new-tag mr-4" data-text="NEW" />
              : null
            }
            <bk-button
              class="add-rule"
              size="small"
              onClick={ (event: Event) => handleShowCreateRule(data, event) }>
              { t('添加授权规则') }
            </bk-button>
          </div>
        </div>
      ),
    },
    {
      label: t('访问DB'),
      field: 'access_db',

      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: PermissionTableRow }) => {
        if (data.rules.length === 0) {
          return (
            <div class="permission-cell">
              <span>{ t('暂无规则') }，</span>
              <bk-button
                theme="primary"
                size="small"
                text
                onClick={ (event: Event) => handleShowCreateRule(data, event) }>
                { t('立即新建') }
              </bk-button>
            </div>
          );
        }

        return (
          getRenderList(data).map(rule => (
            <div class="permission-cell">
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
      render: ({ data }: { data: PermissionTableRow }) => (
        getRenderList(data).map((rule) => {
          const { privilege } = rule;

          return (
            <div class="permission-cell" v-overflow-tips>
              {
                !privilege ? '--' : privilege.replace(/,/g, '，')
              }
            </div>
          );
        })
      ),
    },
    // {
    //   label: t('授权实例'),
    //   field: 'instance',
    //   sort: true,
    //   render: ({ data }: { data: PermissionTableRow }) => (
    //     getRenderList(data).map((rule) => {
    //       const { instance } = rule;

    //       return (
    //         <div class="permission-cell" v-overflow-tips>{ instance || '--'  }</div>
    //       );
    //     })
    //   ),
    // },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: { data: PermissionTableRow }) => {
        if (data.rules.length === 0) {
          return (
            <div class="permission-cell">
              <bk-button
                theme="primary"
                text
                onClick={ () => handleDeleteAccount(data) }>
                { t('删除账号') }
              </bk-button>
            </div>
          );
        }

        return (
          getRenderList(data).map(item => (
            <div class="permission-cell">
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

  const handleClearSearch = () => {
    tableSearch.value = [];
    getList();
  };

  const handleToggleExpand = (data: PermissionTableRow) => {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) return;
    // eslint-disable-next-line no-param-reassign
    data.isExpand = !data.isExpand;
  };

  const addAccountDialogShow = ref(false);
  const accountInfoDialogShow = ref(false);
  const accountInfoDialogInfo = ref({} as PermissionTableRow);

  const handleAddAcount = () => {
    addAccountDialogShow.value = true;
  };

  const handleViewAccount = (data: PermissionTableRow, event: Event) => {
    event.stopPropagation();

    accountInfoDialogShow.value = true;
    accountInfoDialogInfo.value = data;
  };

  const handleDeleteAccountSuccess = () => {
    accountInfoDialogShow.value = false;
    getList();
  };

  const createRuleShow = ref(false);
  const createRuleAccountId = ref(-1);

  const handleShowCreateRule = (row: PermissionTableRow, event: Event) => {
    event.stopPropagation();

    createRuleAccountId.value = row.account.account_id;
    createRuleShow.value = true;
  };

  const handleDeleteAccount = (data: PermissionTableRow) => {
    const { user, account_id: accountId } = data.account;

    deleteAccountReq(user, accountId, handleDeleteAccountSuccess);
  };

  const authorizeShow = ref(false);
  const authorizeUser = ref('');
  const authorizeDbs = ref<string []>([]);

  const handleShowAuthorize = (row: PermissionTableRow, rule: PermissionRuleInfo) => {
    authorizeShow.value = true;
    authorizeUser.value = row.account.user;
    authorizeDbs.value = [rule.access_db];
  };
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.permission {
  .permission-operations {
    justify-content: space-between;
    padding-bottom: 16px;
    .flex-center();
  }

  :deep(.permission-cell) {
    position: relative;
    padding: 0 15px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border-bottom: 1px solid @border-disable;
  }

  :deep(.permission-cell:last-child) {
    border-bottom: 0;
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

  :deep(.user-name) {
    height: 100%;
    padding-left: 24px;
    cursor: pointer;
    align-items: center;
    .flex-center();

    .add-rule {
      display: none;
    }
  }

  :deep(.user-name-text) {
    margin-right: 16px;
    font-weight: bold;
  }
}

.permission-table {
  transition: all 0.5s;

  :deep(.bk-table-body table tbody tr:hover) {
    .add-rule {
      display: flex;
    }

  }

  :deep(.bk-table-body table tbody tr) {
    &.is-new {
      td {
        background-color: #f3fcf5 !important;
      }
    }

    td {
      .cell {
        padding: 0 !important;
      }

    }

    td:first-child {
      .cell,
      .permission-cell {
        height: 100% !important;
      }
    }
  }
}
</style>
