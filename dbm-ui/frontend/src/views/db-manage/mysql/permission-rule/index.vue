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
          v-model="tableSearch"
          :data="filters"
          :placeholder="t('账号名称_DB名称_权限名称')"
          style="width: 500px"
          unique-select
          @change="handleSearchChange" />
      </div>
      <DbTable
        ref="tableRef"
        class="rules-table"
        :columns="columns"
        :data-source="getPermissionRules"
        releate-url-query
        :row-class="setRowClass"
        row-hover="auto"
        @clear-search="handleClearSearch"
        @refresh="fetchData" />
    </div>
    <!-- 创建账户 -->
    <AccountDialog
      v-model="accountDialog.isShow"
      @success="fetchData" />
    <!-- 添加授权规则 -->
    <CreateRuleSlider
      v-model="ruleState.isShow"
      :account-id="ruleState.accountId"
      :rule-obj="ruleState.rowData"
      @success="fetchData" />
    <!-- 集群授权 -->
    <ClusterAuthorize
      ref="clusterAuthorizeRef"
      v-model="authorizeState.isShow"
      :access-dbs="authorizeState.dbs"
      :account-type="AccountTypes.MYSQL"
      :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave', ClusterTypes.TENDBSINGLE]"
      :user="authorizeState.user" />
    <!-- 账号信息 dialog -->
    <BkDialog
      v-model:is-show="accountDetailDialog.isShow"
      dialog-type="show"
      :draggable="false"
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
            {{ column.value ?? accountDetailDialog.rowData?.account[column.key as keyof MysqlPermissonAccountModel['account']] }}
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
              :resource-id="accountDetailDialog.rowData?.account.account_id"
              @click="handleDeleteAccount(accountDetailDialog.rowData)">
              {{ t('删除账号') }}
            </AuthButton>
          </span>
        </div>
      </div>
    </BkDialog>
  </PermissionCatch>
</template>
<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import { differenceInHours } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import {
    deleteAccount,
    getPermissionRules,
  } from '@services/source/permission';
  import type { PermissionRuleInfo } from '@services/types/permission';

  import {
    useTicketCloneInfo,
  } from '@hooks';

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

  import { dbOperations } from './common/const';
  import AccountDialog from './components/AccountDialog.vue';
  import CreateRuleSlider from './components/CreateRule.vue';

  const { t } = useI18n();

  useTicketCloneInfo({
    type: TicketTypes.MYSQL_AUTHORIZE_RULES,
    onSuccess(cloneData) {
      const {
        dbs,
        user,
        clusterType,
        clusterList,
        sourceIpList,
      } = cloneData;
      authorizeState.isShow = true;
      authorizeState.dbs = dbs;
      authorizeState.user = user;
      clusterAuthorizeRef.value!.initSelectorData({
        clusterType,
        clusterList,
        sourceIpList,
      });
      window.changeConfirm = true;
    },
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tableSearch = ref([]);
  const clusterAuthorizeRef = ref<InstanceType<typeof ClusterAuthorize>>();

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
      logical: '&',
      children: [
        ...dbOperations.dml.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.ddl.map(id => ({ id: id.toLowerCase(), name: id })),
        ...dbOperations.glob.map(id => ({ id, name: id })),
      ],
    },
  ];

  // 判断是否为新账号规则
  const isNewUser = (row: MysqlPermissonAccountModel) => {
    const createTime = row.account.create_time;
    if (!createTime) return '';

    const createDay = new Date(createTime);
    const today = new Date();
    return differenceInHours(today, createDay) <= 24;
  };

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
    rowData: {} as MysqlPermissonAccountModel,
  });
  /**
   * 添加授权规则功能
   */
  const ruleState = reactive({
    isShow: false,
    accountId: -1,
    rowData: {} as MysqlPermissonAccountModel['rules'][number],
  });

  const rowExpandMap = shallowRef<Record<number, boolean>>({});

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
                  isNewUser(data) && (
                    <bk-tag
                      size="small"
                      theme="success"
                      class="ml-4">
                      NEW
                    </bk-tag>
                  )
                }
                <auth-button
                  action-id="mysql_add_account_rule"
                  permission={data.permission.mysql_add_account_rule}
                  resource={data.account.account_id}
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
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <span>{t('暂无规则')}，</span>
              <auth-button
                action-id="mysql_add_account_rule"
                permission={data.permission.mysql_add_account_rule}
                resource={data.account.account_id}
                theme="primary"
                size="small"
                text
                onClick={(event: PointerEvent) => handleShowCreateRule(data, event)}>
                {t('立即新建')}
              </auth-button>
            </div>
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
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
        getRenderList(data).map((rule) => {
          const { privilege } = rule;
          return (
            <div class="cell-row pr-12" v-overflow-tips>
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
                theme="primary"
                text
                action-id="mysql_account_delete"
                permission={data.permission.mysql_account_delete}
                resource={data.account.account_id}
                onClick={() => handleDeleteAccount(data)}>
                {t('删除账号')}
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
                onClick={(event: PointerEvent) => handleShowAuthorize(data, item, event)}>
                {t('授权')}
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
  const setRowClass = (row: MysqlPermissonAccountModel) => (isNewUser(row) ? 'is-new' : '');

  const fetchData = () => {
    tableRef.value!.fetchData(
      {
        ...getSearchSelectorParams(tableSearch.value),
      },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        account_type: 'mysql',
      }
    )
  };

  const handleSearchChange = () => {
    fetchData();
  };

  const handleClearSearch = () => {
    tableSearch.value = [];
    fetchData();
  };
  /**
   * 展开/收起渲染列表
   */
  const getRenderList = (data: MysqlPermissonAccountModel) => (!rowExpandMap.value[data.account.account_id]
    ? data.rules : data.rules.slice(0, 1));

  /**
   * 列表项展开/收起
   */
  const handleToggleExpand = (data: MysqlPermissonAccountModel) => {
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


  const handleViewAccount = (row: MysqlPermissonAccountModel, e: MouseEvent) => {
    e?.stopPropagation();
    accountDetailDialog.rowData = row;
    accountDetailDialog.isShow = true;
  };

  /**
   * 删除账号
   */
  const handleDeleteAccount = (row: MysqlPermissonAccountModel) => {
    InfoBox({
      type: 'warning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: row.account.user }),
      onConfirm: async () => {
        try {
          await deleteAccount({
            bizId: window.PROJECT_CONFIG.BIZ_ID,
            account_id: row.account.account_id,
            account_type: 'mysql',
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


  const handleShowCreateRule = (row: MysqlPermissonAccountModel, e: PointerEvent) => {
    e.stopPropagation();
    ruleState.rowData = {} as MysqlPermissonAccountModel['rules'][number];
    ruleState.accountId = row.account.account_id;
    ruleState.isShow = true;
  };

  const handleShowEditRule = (e: PointerEvent, row: MysqlPermissonAccountModel, index: number) => {
    e.stopPropagation();
    ruleState.accountId = row.account.account_id;
    ruleState.rowData = row.rules[index];
    ruleState.isShow = true;
  };


  const handleShowAuthorize = (row: MysqlPermissonAccountModel, rule: PermissionRuleInfo, e: PointerEvent) => {
    e.stopPropagation();
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
  };

  onMounted(() => {
    fetchData()
  })
</script>

<style lang="less" scoped>
  .permission-rules-page {
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
