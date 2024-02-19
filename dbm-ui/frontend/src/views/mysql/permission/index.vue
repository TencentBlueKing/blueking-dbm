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
  <div class="permission-rules-page">
    <BkAlert
      class="permission-info-alert"
      theme="info">
      <template #title>
        <p>
          <span class="label">{{ t('账号') }} ：</span>{{ t('访问 DB 的用户名，包括它的密码') }}
        </p>
        <p>
          <span class="label">{{ t('授权规则') }} ：</span>{{ t('权限模板，预定义账号拥有哪些权限') }}
        </p>
        <p>
          <span class="label">{{ t('授权') }} ：</span>{{ t('根据 grant 语法授予 DB 实例的访问权限') }}
        </p>
      </template>
    </BkAlert>
    <div class="operation-box">
      <AuthButton
        action-id="mysql_account_create"
        theme="primary"
        @click="handleShowAccountDialog">
        {{ t('新建账号') }}
      </AuthButton>
      <DbSearchSelect
        v-model="state.search"
        :data="filters"
        :placeholder="t('账号名称_DB名称_权限名称')"
        style="width: 500px;"
        unique-select
        @change="handleSearchChange" />
    </div>
    <BkLoading :loading="state.isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="state.data"
        :is-anomalies="state.isAnomalies"
        :is-searching="state.search.length > 0"
        :max-height="tableMaxHeight"
        :row-class="setRowClass"
        @clear-search="handleClearSearch"
        @refresh="fetchData" />
    </BkLoading>
  </div>
  <!-- 创建账户 -->
  <AccountDialog
    v-model="accountDialog.isShow"
    @success="fetchData" />
  <!-- 添加授权规则 -->
  <CreateRuleSlider
    v-model="ruleState.isShow"
    :account-id="ruleState.accountId"
    @success="fetchData" />
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeState.isShow"
    :access-dbs="authorizeState.dbs"
    :user="authorizeState.user" />
  <!-- 账号信息 dialog -->
  <BkDialog
    v-model:is-show="accountDetailDialog.isShow"
    dialog-type="show"
    :draggable="false"
    height="auto"
    quick-close
    :title="t('账号信息')"
    :width="480">
    <div class="permission-rule-account-details">
      <div
        v-for="column of accountColumns"
        :key="column.key"
        class="account-details-item">
        <span class="account-details-label">{{ column.label }}：</span>
        <span class="account-details-value">
          {{ column.value ?? accountDetailDialog.rowData?.account[column.key as keyof IPermissioRule['account']] }}
        </span>
      </div>
      <div
        v-if="accountDetailDialog.rowData?.rules?.length === 0"
        class="account-details-item">
        <span class="account-details-label" />
        <span class="account-details-value">
          <AuthButton
            action-id="mysql_account_delete"
            hover-theme="danger"
            @click="handleDeleteAccount(accountDetailDialog.rowData)">
            {{ t('删除账号') }}
          </AuthButton>
        </span>
      </div>
    </div>
  </BkDialog>
</template>
<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { differenceInHours } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import {
    deleteAccount,
    getPermissionRules,
  } from '@services/permission';
  import type {
    PermissionRuleInfo,
  } from '@services/types/permission';

  import {
    useInfoWithIcon,
    useTableMaxHeight,
  } from '@hooks';

  import { OccupiedInnerHeight } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  import { dbOperations } from './common/const';
  import AccountDialog from './components/AccountDialog.vue';
  import CreateRuleSlider from './components/CreateRule.vue';

  type IPermissioRule = ServiceReturnType<typeof getPermissionRules>['results'][number]

  const { t } = useI18n();

  /**
   * search select 过滤参数
   */
  const filters = [
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
      children: [
        ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.glob.map(id => ({ id, name: id })),
      ],
    },
  ];

  // 判断是否为新账号规则
  const isNewUser = (row: IPermissioRule) => {
    const createTime = row.account.create_time;
    if (!createTime) return '';

    const createDay = new Date(createTime);
    const today = new Date();
    return differenceInHours(today, createDay) <= 24;
  };

  const state = reactive({
    isAnomalies: false,
    isLoading: false,
    search: [] as ISearchValue[],
    data: [] as IPermissioRule[],
  });
  /**
   * 集群授权
   */
  const authorizeState = reactive({
    isShow: false,
    user: '',
    dbs: [] as string[],
  });
  // 新建账号功能
  const accountDialog = reactive({
    isShow: false,
  });
  // 账号信息查看
  const accountDetailDialog = reactive({
    isShow: false,
    rowData: {} as IPermissioRule,
  });
  /**
   * 添加授权规则功能
   */
  const ruleState = reactive({
    isShow: false,
    accountId: -1,
  });

  const rowExpandMap = shallowRef<Record<number, boolean>>({});

  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION_WITH_TIP);

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: IPermissioRule }) => (
        <TextOverflowLayout>
          {{
            prepend: () => (
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
                isNewUser(data) && (
                  <span
                    class="glob-new-tag mr-4"
                    data-text="NEW" />
                )
                }
                <auth-button
                  action-id="mysql_account_rule_create"
                  permission={data.permission.mysql_account_rule_create}
                  class="add-rule-btn"
                  size="small"
                  onClick={(event: PointerEvent) => handleShowCreateRule(data, event)}>
                  {t('添加授权规则')}
                </auth-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('访问的DB名'),
      field: 'access_db',
      render: ({ data }: { data: IPermissioRule }) => {
        if (data.rules.length === 0) {
          return (
            <>
              <span>{t('暂无规则')}，</span>
              <auth-button
                action-id="mysql_account_rule_create"
                permission={data.permission.mysql_account_rule_create}
                theme="primary"
                size="small"
                text
                onClick={(event: PointerEvent) => handleShowCreateRule(data, event)}>
                {t('立即新建')}
              </auth-button>
            </>
          );
        }

        return (
          getRenderList(data)
            .map(rule => (
              <div class="cell-row">
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
      render: ({ data }: { data: IPermissioRule }) => (
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
      width: 80,
      render: ({ data }: { data: IPermissioRule }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <auth-button
                theme="primary"
                text
                action-id="mysql_account_delete"
                permission={data.permission.mysql_account_delete}
                onClick={() => handleDeleteAccount(data)}>
                {t('删除账号')}
              </auth-button>
            </div>
          );
        }

        return (
          getRenderList(data).map(item => (
            <div class="cell-row">
              <bk-button
                theme="primary"
                text
                onClick={(event: PointerEvent) => handleShowAuthorize(data, item, event)}>
                {t('授权')}
              </bk-button>
            </div>
          ))
        );
      },
    },
  ];

  const accountColumns = [
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
      key: 'create_time',
    },
    {
      label: t('创建人'),
      key: 'creator',
    },
  ];
  // 设置行样式
  const setRowClass = (row: IPermissioRule) => (isNewUser(row) ? 'is-new' : '');

  const fetchData = () => {
    getPermissionRules({
      ...getSearchSelectorParams(state.search),
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    })
      .then((res) => {
        state.data = res.results.map(item => Object.assign({ isExpand: true }, item));
      })
      .catch(() => {
        state.data = [];
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  const handleSearchChange = () => {
    fetchData();
  };

  const handleClearSearch = () => {
    state.search = [];
    fetchData();
  };
  /**
   * 展开/收起渲染列表
   */
  const getRenderList = (data: IPermissioRule) => (!rowExpandMap.value[data.account.account_id]
    ? data.rules : data.rules.slice(0, 1));

  /**
   * 列表项展开/收起
   */
  const handleToggleExpand = (data: IPermissioRule) => {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) {
      return;
    }
    const expandMap = { ...rowExpandMap.value };
    expandMap[data.account.account_id] = !expandMap[data.account.account_id];
    rowExpandMap.value = expandMap;
  };


  const handleShowAccountDialog = () => {
    accountDialog.isShow = true;
  };


  const handleViewAccount = (row: IPermissioRule, e: MouseEvent) => {
    e?.stopPropagation();
    accountDetailDialog.rowData = row;
    accountDetailDialog.isShow = true;
  };

  /**
   * 删除账号
   */
  const handleDeleteAccount = (row: IPermissioRule) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: row.account.user }),
      onConfirm: async () => {
        try {
          await deleteAccount({
            bizId: window.PROJECT_CONFIG.BIZ_ID,
            account_id: row.account.account_id,
          });
          Message({
            message: t('成功删除账号'),
            theme: 'success',
          });
          accountDetailDialog.isShow = false;
          fetchData();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };


  const handleShowCreateRule = (row: IPermissioRule, e: PointerEvent) => {
    e.stopPropagation();
    ruleState.accountId = row.account.account_id;
    ruleState.isShow = true;
  };


  const handleShowAuthorize = (row: IPermissioRule, rule: PermissionRuleInfo, e: PointerEvent) => {
    e.stopPropagation();
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
  };
</script>
<style lang="less">
@import "@styles/mixins.less";

.permission-rules-page {
  .bk-table {
    .cell{
      padding: 0 !important;
    }

    tr{
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

    th,
    td{
      &:first-child{
        padding: 0 16px;
      }
    }
  }

  .permission-info-alert {
    margin-bottom: 16px;

    .label {
      font-weight: 700;
    }
  }

  .operation-box {
    justify-content: space-between;
    padding-bottom: 16px;
    .flex-center();
  }

  .cell-row{
    & ~ .cell-row{
      border-top: 1px solid #DCDEE5;
    }
  }

  .row-expand-btn {
    display: flex;
    padding-right: 8px;
    cursor: pointer;
    align-items: center;
    justify-content: center;

    .expand-flag{
      transform: rotate(-90deg);
      transition: all 0.1s;

      &.is-expand {
        transform: rotate(0);
      }
    }
  }

  .add-rule-btn{
    display: none;
  }
}

.permission-rule-account-details {
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
