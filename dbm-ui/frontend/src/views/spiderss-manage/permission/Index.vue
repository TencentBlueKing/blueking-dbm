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
        {{ $t('新建账号') }}
      </BkButton>
      <DbSearchSelect
        v-model="state.search"
        :data="filters"
        :placeholder="$t('请输入账号名称/DB名称/权限名称')"
        style="width: 500px;"
        unique-select
        @change="getList" />
    </div>
    <BkLoading :loading="state.isLoading">
      <DbOriginalTable
        class="permission__table"
        :columns="columns"
        :data="state.data"
        :is-anomalies="state.isAnomalies"
        :is-searching="state.search.length > 0"
        :max-height="tableMaxHeight"
        :row-class="setRowClass"
        row-hover="auto"
        show-overflow-tooltip
        @clear-search="handleClearSearch" />
    </BkLoading>
    <AddAccountDialog
      v-model:is-show="addAccountDialogShow"
      @success="getList" />
    <AccountInfoDialog
      v-model:is-show="accountInfoDialogState.isShow"
      :info="accountInfoDialogState.info"
      @delete-account="handleDeleteAccountSuccess" />
    <CreateRule
      v-model:is-show="createRuleState.isShow"
      :account-id="createRuleState.accountId"
      @success="getList" />
    <ClusterAuthorize
      v-model:is-show="authorizeState.isShow"
      :access-dbs="authorizeState.dbs"
      :cluster-type="ClusterTypes.TENDBCLUSTER"
      :user="authorizeState.user" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { PermissionInfo } from  '@services/spider/permission';

  import { useTableMaxHeight  } from '@hooks';

  import { ClusterTypes, OccupiedInnerHeight } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { dbOperations } from './common/consts';
  import type { PermissionState, PermissionTableRow } from './common/types';
  import { getRenderList, isNewUser } from './common/utils';
  import AccountInfoDialog from './components/AccountInfoDialog.vue';
  import AddAccountDialog from './components/AddAccountDialog.vue';
  import CreateRule from './components/CreateRule.vue';
  import { useDeleteAccount } from './hooks/useDeleteAccount';
  import { usePermissionList } from './hooks/usePermissionList';

  const { t } = useI18n();

  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);
  const setRowClass = (row: PermissionTableRow) => (isNewUser(row) ? 'is-new' : '');

  const state = reactive<PermissionState>({
    isAnomalies: false,
    isLoading: false,
    search: [],
    data: [],
  });

  const { getList } = usePermissionList(state);
  const { deleteAccountReq } = useDeleteAccount();

  const filters = [{
    name: t('账号名称'),
    id: 'user',
  }, {
    name: t('访问DB'),
    id: 'access_db',
  }, {
    name: t('权限'),
    id: 'privilege',
    multiple: true,
    children: [
      ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
      ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
      ...dbOperations.glob.map(id => ({ id, name: id })),
    ],
  }];

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ data }: { data: PermissionTableRow }) => (
      <div class="permission__cell" onClick={ handleToggleExpand.bind(null, data) }>
        {
          data.rules.length > 1
            ? <i class={['db-icon-down-shape user-icon', { 'user-icon__expand': data.isExpand }]} />
            : null
        }
        <div class="user-name">
          <a v-overflow-tips class="user-name__text text-overflow" href="javascript:" onClick={ handleViewAccount.bind(null, data) }>{ data.account.user }</a>
          <bk-button class="add-rule" size="small" onClick={ handleShowCreateRule.bind(null, data)}>{t('添加授权规则') }</bk-button>
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
          <div class="permission__cell">
            <span>{t('暂无规则')}，</span>
            <bk-button theme="primary" size="small" text onClick={ handleShowCreateRule.bind(null, data) }>
              {t('立即新建')}
            </bk-button>
          </div>
          );
        }

        return (
          getRenderList(data).map(rule => (
          <div class="permission__cell">
            <bk-tag>{rule.access_db || '--'}</bk-tag>
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
            <div class="permission__cell" v-overflow-tips>
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
    //         <div class="permission__cell" v-overflow-tips>{ instance || '--'  }</div>
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
          <div class="permission__cell">
            <bk-button theme="primary" text onClick={ handleDeleteAccount.bind(null, data)}>{t('删除账号') }</bk-button>
          </div>
          );
        }

        return (
          getRenderList(data).map(item => (
          <div class="permission__cell">
            <bk-button theme="primary" text onClick={ handleShowAuthorize.bind(null, data, item)}>{t('授权实例') }</bk-button>
          </div>
          ))
        );
      },
    },
  ];

  const handleClearSearch = () => {
    state.search = [];
    getList();
  };

  const handleToggleExpand = (data: PermissionTableRow) => {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) return;
    // eslint-disable-next-line no-param-reassign
    data.isExpand = !data.isExpand;
  };


  const addAccountDialogShow = ref(false);
  const accountInfoDialogState = reactive({
    isShow: false,
    info: {},
  });

  const handleAddAcount = () => {
    addAccountDialogShow.value = true;
  };

  const handleViewAccount = (data: PermissionTableRow, e: Event) => {
    e.stopPropagation();

    accountInfoDialogState.isShow = true;
    accountInfoDialogState.info = data;
  };

  const handleDeleteAccountSuccess = () => {
    accountInfoDialogState.isShow = false;
    getList();
  };

  const createRuleState = reactive({
    isShow: false,
    accountId: -1,
  });

  const handleShowCreateRule = (row: PermissionTableRow, e: Event) => {
    e.stopPropagation();

    createRuleState.accountId = row.account.account_id;
    createRuleState.isShow = true;
  };

  const handleDeleteAccount = (data: PermissionTableRow) => {
    const { user, account_id: accountId } = data.account;

    deleteAccountReq(user, accountId, handleDeleteAccountSuccess);
  };

  const authorizeState = reactive({
    isShow: false,
    user: '',
    dbs: [] as string[],
  });

  const handleShowAuthorize = (row: PermissionTableRow, rule: PermissionInfo) => {
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
  };
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.permission {
  &-operations {
    justify-content: space-between;
    padding-bottom: 16px;
    .flex-center();
  }

  :deep(&__cell) {
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

    &__expand {
      transform: translateY(-50%) rotate(0);
    }
  }

  :deep(.user-name) {
    height: 100%;
    padding-left: 24px;
    cursor: pointer;
    align-items: center;
    .flex-center();

    &__text {
      margin-right: 16px;
      font-weight: bold;
    }

    .add-rule {
      display: none;
    }
  }

  &__table {
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
          .permission__cell {
            height: 100% !important;
          }
        }
      }
    }
  }
}
</style>
./common/consts
