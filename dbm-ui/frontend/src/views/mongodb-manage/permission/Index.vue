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
  <div class="mongo-permission">
    <div class="mongo-permission-operations">
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
    <DbTable
      ref="tableRef"
      class="mongo-permission-table"
      :columns="columns"
      :data-source="getMongodbPermissionRules"
      :row-class="setRowClass"
      row-hover="auto"
      @clear-search="handleClearSearch" />
    <CreateAccountDialog
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
      :account-type="AccountTypes.MONGODB"
      :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
      :user="authorizeUser" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongoPermissonAccountModel from '@services/model/mongo-permission/mongo-permission-account';
  import { getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import type { PermissionRuleInfo } from '@services/types/permission';

  import {
    AccountTypes,
    ClusterTypes,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { getSearchSelectorParams } from '@utils';

  import { dbOperations } from './common/consts';
  import AccountInfoDialog from './components/AccountInfoDialog.vue';
  import CreateAccountDialog from './components/CreateAccountDialog.vue';
  import CreateRule from './components/CreateRule.vue';
  import { useDeleteAccount } from './hooks/useDeleteAccount';

  const { t } = useI18n();
  const { deleteAccountReq } = useDeleteAccount();

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
        ...dbOperations.mongo_user.map(id => ({
          id: id.toLowerCase(),
          name: id,
        })),
        ...dbOperations.mongo_manager.map(id => ({
          id: id.toLowerCase(),
          name: id,
        })),
      ],
    },
  ];

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: MongoPermissonAccountModel }) => (
        <div
          class="mongo-permission-cell"
          onClick={ () => handleToggleExpand(data) }>
          {
            data.rules.length > 1 && (
              <db-icon
                type="down-shape"
                class={['user-icon', {
                  'user-icon-expand': data.isExpand,
                }]} />
            )
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
              data.isNewRow && (
                <span
                  class="glob-new-tag ml-6"
                  data-text="NEW" />
              )
            }
            <bk-button
              class="add-rule-button ml-6"
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
      render: ({ data }: { data: MongoPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="mongo-permission-cell">
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
          data.renderList.map(rule => (
            <div class="mongo-permission-cell">
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
      render: ({ data }: { data: MongoPermissonAccountModel }) => {
        if (data.rules.length > 0) {
          data.renderList.map((rule) => {
            const { privilege } = rule;

            return (
              <div class="mongo-permission-cell" v-overflow-tips>
                {
                  privilege ? privilege.replace(/,/g, '，') : '--'
                }
              </div>
            );
          });
        }

        return <div class="mongo-permission-cell">--</div>;
      },
    },
    // {
    //   label: t('授权实例'),
    //   field: 'instance',
    //   sort: true,
    //   render: ({ data }: { data: MongoPermissonAccountModel }) => (
    //     data.renderList.map((rule) => {
    //       const { instance } = rule;

    //       return (
    //         <div class="mongo-permission-cell" v-overflow-tips>{ instance || '--'  }</div>
    //       );
    //     })
    //   ),
    // },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: { data: MongoPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="mongo-permission-cell">
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
          data.renderList.map(item => (
            <div class="mongo-permission-cell">
              <bk-button
                theme="primary"
                text
                onClick={ () => handleShowAuthorize(data, item) }>
                { t('授权实例') }
              </bk-button>
            </div>
          ))
        );
      },
    },
  ];

  const tableRef = ref();
  const tableSearch = ref([]);
  const addAccountDialogShow = ref(false);
  const accountInfoDialogShow = ref(false);
  const accountInfoDialogInfo = ref({} as MongoPermissonAccountModel);
  const authorizeShow = ref(false);
  const authorizeUser = ref('');
  const authorizeDbs = ref<string[]>([]);
  const createRuleShow = ref(false);
  const createRuleAccountId = ref(-1);

  const setRowClass = (row: MongoPermissonAccountModel) => (row.isNewRow ? 'is-new' : '');

  const getList = () => {
    tableRef.value.fetchData({
      ...getSearchSelectorParams(tableSearch.value),
      account_type: AccountTypes.MONGODB,
    });
  };

  const handleClearSearch = () => {
    tableSearch.value = [];
    getList();
  };

  const handleToggleExpand = (data: MongoPermissonAccountModel) => {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) {
      return;
    }
    Object.assign(data, { isExpand: !data.isExpand });
  };

  const handleAddAcount = () => {
    addAccountDialogShow.value = true;
  };

  const handleViewAccount = (data: MongoPermissonAccountModel, event: Event) => {
    event.stopPropagation();

    accountInfoDialogShow.value = true;
    accountInfoDialogInfo.value = data;
  };

  const handleDeleteAccountSuccess = () => {
    accountInfoDialogShow.value = false;
    getList();
  };

  const handleShowCreateRule = (row: MongoPermissonAccountModel, event: Event) => {
    event.stopPropagation();

    createRuleAccountId.value = row.account.account_id;
    createRuleShow.value = true;
  };

  const handleDeleteAccount = (data: MongoPermissonAccountModel) => {
    const {
      user,
      account_id: accountId,
    } = data.account;

    deleteAccountReq(user, accountId, handleDeleteAccountSuccess);
  };

  const handleShowAuthorize = (row: MongoPermissonAccountModel, rule: PermissionRuleInfo) => {
    authorizeShow.value = true;
    authorizeUser.value = row.account.user;
    authorizeDbs.value = [rule.access_db];
  };
</script>

<style lang="less" scoped>
.mongo-permission {
  .mongo-permission-operations {
    display: flex;
    padding-bottom: 16px;
    justify-content: space-between;
    align-items: center;
  }

  :deep(.mongo-permission-cell) {
    position: relative;
    padding: 0 15px;
    overflow: hidden;
    line-height: calc(var(--row-height) - 1px);
    text-overflow: ellipsis;
    white-space: nowrap;
    border-bottom: 1px solid @border-disable;
  }

  :deep(.mongo-permission-cell:last-child) {
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
    display: flex;
    height: 100%;
    padding-left: 24px;
    cursor: pointer;
    align-items: center;

    .add-rule-button {
      display: none;
    }
  }

  :deep(.user-name-text) {
    margin-right: 16px;
    font-weight: bold;
  }
}

:deep(.mongo-permission-table) {
  transition: all 0.5s;

  tr:hover {
    .add-rule-button {
      display: flex;
    }
  }

  .is-new {
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
    .mongo-permission-cell {
      height: 100% !important;
    }
  }
}
</style>
