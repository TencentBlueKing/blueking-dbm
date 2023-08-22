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
  <div class="permission-rules">
    <div class="permission-rules__operations">
      <BkButton
        theme="primary"
        @click="handleShowAccountDialog">
        {{ $t('新建账号') }}
      </BkButton>
      <DbSearchSelect
        v-model="state.search"
        :data="filters"
        :placeholder="$t('账号名称_DB名称_权限名称')"
        style="width: 500px;"
        unique-select
        @change="handleSearch" />
    </div>
    <BkLoading :loading="state.isLoading">
      <DbOriginalTable
        class="permission-rules__table"
        :columns="columns"
        :data="state.data"
        :is-anomalies="state.isAnomalies"
        :is-searching="state.search.length > 0"
        :max-height="tableMaxHeight"
        :row-class="setRowClass"
        @clear-search="handleClearSearch"
        @refresh="getRules" />
    </BkLoading>
  </div>
  <!-- 创建账户 -->
  <AccountDialog
    v-model="accountDialog.isShow"
    @success="getRules" />
  <!-- 添加授权规则 -->
  <CreateRuleSlider
    v-model="ruleState.isShow"
    :account-id="ruleState.accountId"
    @success="getRules" />
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
    :title="$t('账号信息')"
    :width="480">
    <div class="account-details">
      <div
        v-for="column of accountColumns"
        :key="column.key"
        class="account-details__item">
        <span class="account-details__label">{{ column.label }}：</span>
        <span class="account-details__value">
          {{ column.value ?? accountDetailDialog.rowData?.account?.[column.key] }}
        </span>
      </div>
      <div
        v-if="accountDetailDialog.rowData?.rules?.length === 0"
        class="account-details__item">
        <span class="account-details__label" />
        <span class="account-details__value">
          <BkButton
            hover-theme="danger"
            @click="handleDeleteAccount(accountDetailDialog.rowData)">{{ $t('删除账号') }}</BkButton>
        </span>
      </div>
    </div>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import { differenceInHours } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import { deleteAccount } from '@services/permission';
  import type { PermissionRuleAccount, PermissionRuleInfo  } from '@services/types/permission';

  import { useInfoWithIcon, useTableMaxHeight } from '@hooks';

  import { OccupiedInnerHeight } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';

  import { dbOperations } from './common/const';
  import type { PermissionRuleExtend, PermissionRulesState } from './common/types';
  import AccountDialog from './components/AccountDialog.vue';
  import CreateRuleSlider from './components/CreateRule.vue';
  import { usePermissionRules } from './hooks/usePermissionRules';

  const { t } = useI18n();

  const state = reactive<PermissionRulesState>({
    isAnomalies: false,
    isLoading: false,
    search: [],
    data: [],
  });

  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);
  const {
    bizId,
    getRules,
  } = usePermissionRules(state);
  getRules();

  const handleClearSearch = () => {
    state.search = [];
    getRules();
  };

  /**
   * search select 过滤参数
   */
  const filters = [{
    name: t('账号名称'),
    id: 'user',
  }, {
    name: t('DB名称'),
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

  /**
   * search select 触发搜索
   */
  function handleSearch() {
    nextTick(getRules);
  }

  // 判断是否为新账号规则
  const isNewUser = (row: PermissionRuleExtend) => {
    const createTime = row.account.create_time;
    if (!createTime) return '';

    const createDay = new Date(createTime);
    const today = new Date();
    return differenceInHours(today, createDay) <= 24;
  };

  const columns = [{
    label: t('账号名称'),
    field: 'user',
    showOverflowTooltip: false,
    render: ({ data }: { data: PermissionRuleExtend }) => (
      <div class="permission-rules__cell" onClick={handleToggleExpand.bind(this, data)}>
        {
          data.rules.length > 1
            ? <i class={['db-icon-down-shape user-icon', { 'user-icon__expand': data.isExpand }]} />
            : null
        }
        <div class="user-name">
          <a v-overflow-tips class="user-name__text text-overflow" href="javascript:" onClick={handleViewAccount.bind(null, data)}>{data.account.user}</a>
          {isNewUser(data) ? <span class="glob-new-tag mr-4" data-text="NEW" /> : null}
          <bk-button class="add-rule" size="small" onClick={handleShowCreateRule.bind(null, data)}>{t('添加授权规则')}</bk-button>
        </div>
      </div>
    ),
  }, {
    label: t('访问的DB名'),
    field: 'access_db',
    render: ({ data }: { data: PermissionRuleExtend }) => {
      if (data.rules.length === 0) {
        return (
          <div class="permission-rules__cell">
            <span>{t('暂无规则')}，</span>
            <bk-button theme="primary" size="small" text onClick={handleShowCreateRule.bind(null, data)}>
              {t('立即新建')}
            </bk-button>
          </div>
        );
      }

      return (
        getRenderList(data).map(rule => (
          <div class="permission-rules__cell">
            <bk-tag>{rule.access_db || '--'}</bk-tag>
          </div>
        ))
      );
    },
  }, {
    label: t('权限'),
    field: 'privilege',
    showOverflowTooltip: false,
    render: ({ data }: { data: PermissionRuleExtend }) => (
      getRenderList(data).map((rule) => {
        const { privilege } = rule;
        return (
          <div class="permission-rules__cell" v-overflow-tips>
            {
              !privilege ? '--' : privilege.replace(/,/g, '，')
            }
          </div>
        );
      })
    ),
  }, {
    label: t('操作'),
    width: 140,
    render: ({ data }: { data: PermissionRuleExtend }) => {
      if (data.rules.length === 0) {
        return (
          <div class="permission-rules__cell">
            <bk-button theme="primary" text onClick={handleDeleteAccount.bind(this, data)}>{t('删除账号')}</bk-button>
          </div>
        );
      }

      return (
        getRenderList(data).map(item => (
          <div class="permission-rules__cell">
            <bk-button theme="primary" text onClick={handleShowAuthorize.bind(this, data, item)}>{t('授权')}</bk-button>
          </div>
        ))
      );
    },
  }];
  // 设置行样式
  const setRowClass = (row: PermissionRuleExtend) => (isNewUser(row) ? 'is-new' : '');

  /**
   * 展开/收起渲染列表
   */
  function getRenderList(data: PermissionRuleExtend) {
    return data.isExpand ? data.rules : data.rules.slice(0, 1);
  }

  /**
   * 列表项展开/收起
   */
  function handleToggleExpand(data: PermissionRuleExtend) {
    // 长度小于等于 2 则没有展开收起功能
    if (data.rules.length <= 1) return;
    // eslint-disable-next-line no-param-reassign
    data.isExpand = !data.isExpand;
  }

  // 新建账号功能
  const accountDialog = reactive({
    isShow: false,
  });
  function handleShowAccountDialog() {
    accountDialog.isShow = true;
  }

  // 账号信息查看
  const accountDetailDialog = reactive({
    isShow: false,
    rowData: {} as PermissionRuleExtend,
  });
  const accountColumns: Array<{
    label: string,
    key: keyof PermissionRuleAccount,
    value?: string
  }> = [{
    label: t('账号名'),
    key: 'user',
  }, {
    label: t('密码'),
    key: 'password',
    value: '****************',
  }, {
    label: t('创建时间'),
    key: 'create_time',
  }, {
    label: t('创建人'),
    key: 'creator',
  }];
  function handleViewAccount(row: PermissionRuleExtend, e: MouseEvent) {
    e?.stopPropagation();
    accountDetailDialog.rowData = row;
    accountDetailDialog.isShow = true;
  }

  /**
   * 删除账号
   */
  function handleDeleteAccount(row: PermissionRuleExtend) {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: row.account.user }),
      onConfirm: async () => {
        try {
          await deleteAccount(bizId.value, row.account.account_id);
          Message({
            message: t('成功删除账号'),
            theme: 'success',
            delay: 1500,
          });
          accountDetailDialog.isShow = false;
          getRules();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  /**
   * 添加授权规则功能
   */
  const ruleState = reactive({
    isShow: false,
    accountId: -1,
  });

  function handleShowCreateRule(row: PermissionRuleExtend, e: PointerEvent) {
    e.stopPropagation();
    ruleState.accountId = row.account.account_id;
    ruleState.isShow = true;
  }

  /**
   * 集群授权
   */
  const authorizeState = reactive({
    isShow: false,
    user: '',
    dbs: [] as string[],
  });

  function handleShowAuthorize(row: PermissionRuleExtend, rule: PermissionRuleInfo, e: PointerEvent) {
    e.stopPropagation();
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
  }
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.permission-rules {
  &__operations {
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
          .permission-rules__cell {
            height: 100% !important;
          }
        }
      }
    }
  }
}

.account-details {
  font-size: @font-size-mini;

  &__item {
    display: flex;
    padding-bottom: 16px;
  }

  &__label {
    width: 90px;
    text-align: right;
    flex-shrink: 0;
  }

  &__value {
    color: @title-color;
  }
}
</style>
