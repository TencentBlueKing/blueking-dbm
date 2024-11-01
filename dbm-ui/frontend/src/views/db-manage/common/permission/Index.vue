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
          :action-id="`${accountType}_account_create`"
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
        :data-source="configMap[accountType].dataSource"
        releate-url-query
        :row-class="setRowClass"
        row-hover="auto"
        @clear-search="handleClearSearch"
        @refresh="fetchData" />
    </div>
    <!-- 创建账户 -->
    <AccountCreate
      v-model="accountDialog.isShow"
      :account-type="accountType"
      @success="fetchData" />
    <!-- 账号信息 -->
    <AccountDetail
      v-model="accountDetailDialog.isShow"
      :data="accountDetailDialog.rowData"
      @delete-account="handleDeleteAccount" />
    <!-- 添加授权规则 -->
    <Component
      :is="configMap[accountType].createRuleComponent"
      v-model="ruleState.isShow"
      :account-id="ruleState.accountId"
      :account-type="accountType"
      :rule-obj="ruleState.rowData"
      @success="fetchData" />
    <!-- 集群授权 -->
    <ClusterAuthorize
      ref="clusterAuthorizeRef"
      v-model="authorizeState.isShow"
      :access-dbs="authorizeState.dbs"
      :account-type="accountType"
      :cluster-types="configMap[accountType].clusterTypes"
      :rules="authorizeState.rules"
      :user="authorizeState.user" />
  </PermissionCatch>
</template>
<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import { differenceInHours } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import { deleteAccount as deleteMongodbAccount, getPermissionRules as getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { deleteAccount as deleteMysqlAccount, getPermissionRules as getMysqlPermissionRules } from '@services/source/mysqlPermissionAccount';
  import { deleteAccount as deleteSqlserverAccount, getPermissionRules as getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import type { PermissionRule, PermissionRuleInfo } from '@services/types/permission';

  import {
    useTicketCloneInfo,
  } from '@hooks';
  import type { CloneDataHandlerMapKeys } from '@hooks/useTicketCloneInfo/generateCloneData';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import PermissionCatch from '@components/apply-permission/Catch.vue'
  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import MongoCreateRule from '@views/db-manage/common/permission/components/mongo/CreateRule.vue';
  import MysqlCreateRule from '@views/db-manage/common/permission/components/mysql/create-rule/Index.vue';
  import SqlserverCreateRule from '@views/db-manage/common/permission/components/sqlserver/CreateRule.vue';

  import { getSearchSelectorParams } from '@utils';

  import AccountCreate from './components/common/AccountCreate.vue';
  import AccountDetail from './components/common/AccountDetail.vue';
  import mongoDbOperations from './components/mongo/config';
  import mysqlDbOperations from './components/mysql/config';
  import sqlserverDbOperations from './components/sqlserver/config';

  interface Props {
    accountType: AccountTypes;
  }

  const props = defineProps<Props>();

  const configMap = {
    [AccountTypes.MYSQL]: {
      ticketType: TicketTypes.MYSQL_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.TENDBHA, 'tendbhaSlave', ClusterTypes.TENDBSINGLE],
      dbOperations: mysqlDbOperations[AccountTypes.MYSQL].dbOperations,
      dataSource: getMysqlPermissionRules,
      deleteAccount: deleteMysqlAccount,
      createRuleComponent: MysqlCreateRule,
    },
    [AccountTypes.TENDBCLUSTER]: {
      ticketType: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave'],
      dbOperations: mysqlDbOperations[AccountTypes.TENDBCLUSTER].dbOperations,
      dataSource: getMysqlPermissionRules,
      deleteAccount: deleteMysqlAccount,
      createRuleComponent: MysqlCreateRule,
    },
    [AccountTypes.SQLSERVER]: {
      ticketType: TicketTypes.SQLSERVER_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
      dbOperations: sqlserverDbOperations,
      dataSource: getSqlserverPermissionRules,
      deleteAccount: deleteSqlserverAccount,
      createRuleComponent: SqlserverCreateRule,
    },
    [AccountTypes.MONGODB]: {
      ticketType: TicketTypes.MONGODB_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
      dbOperations: mongoDbOperations,
      dataSource: getMongodbPermissionRules,
      deleteAccount: deleteMongodbAccount,
      createRuleComponent: MongoCreateRule,
    },
  };

  const { t } = useI18n();

  useTicketCloneInfo({
    type: configMap[props.accountType].ticketType as CloneDataHandlerMapKeys,
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
      clusterAuthorizeRef.value!.init({
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

  const isMysql = computed(() => props.accountType === AccountTypes.MYSQL || props.accountType === AccountTypes.TENDBCLUSTER);

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
      children: Object.values(configMap[props.accountType].dbOperations).reduce<{
        id: string;
        name: string;
      }[]>((acc, item) => {
        acc.push(...item.map((id) => ({ id: id.toLowerCase(), name: id })));
        return acc;
      }, [])
    },
  ];

  // 判断是否为新账号规则
  const isNewUser = (row: PermissionRule) => {
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
    rules: [] as PermissionRule['rules'],
  });
  // 新建账号功能
  const accountDialog = reactive({
    isShow: false,
  });
  // 账号信息查看
  const accountDetailDialog = reactive({
    isShow: false,
    rowData: {} as PermissionRule,
  });
  /**
   * 添加授权规则功能
   */
  const ruleState = reactive({
    isShow: false,
    accountId: -1,
    rowData: {} as PermissionRuleInfo,
  });

  const rowExpandMap = shallowRef<Record<number, boolean>>({});

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      render: ({ data }: { data: PermissionRule }) => (
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
      render: ({ data }: { data: PermissionRule }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <span>{t('暂无规则')}，</span>
              <auth-button
                action-id={`${props.accountType}_add_account_rule`}
                permission={data.permission[`${props.accountType}_add_account_rule`]}
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
      render: ({ data }: { data: PermissionRule }) => (
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
      render: ({ data }: { data: PermissionRule }) => {
        if (data.rules.length === 0) {
          return (
            <div class="cell-row">
              <auth-button
                theme="primary"
                text
                action-id={`${props.accountType}_account_delete`}
                permission={data.permission[`${props.accountType}_account_delete`]}
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
              {
                isMysql.value &&
                <bk-button
                  theme="primary"
                  class="ml-8"
                  text
                  onClick={(event: PointerEvent) => handleShowEditRule(event, data, index)}>
                  {t('编辑')}
                </bk-button>
              }
            </div>
          ))
        );
      },
    },
  ];

  // 设置行样式
  const setRowClass = (row: PermissionRule) => (isNewUser(row) ? 'is-new' : '');

  const fetchData = () => {
    tableRef.value!.fetchData(
      {
        ...getSearchSelectorParams(tableSearch.value),
      },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        account_type: props.accountType,
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
  const getRenderList = (data: PermissionRule) => (!rowExpandMap.value[data.account.account_id]
    ? data.rules : data.rules.slice(0, 1));

  /**
   * 列表项展开/收起
   */
  const handleToggleExpand = (data: PermissionRule) => {
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


  const handleViewAccount = (row: PermissionRule, e: MouseEvent) => {
    e?.stopPropagation();
    accountDetailDialog.rowData = row;
    accountDetailDialog.isShow = true;
  };

  /**
   * 删除账号
   */
  const handleDeleteAccount = (row: PermissionRule) => {
    InfoBox({
      type: 'warning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: row.account.user }),
      onConfirm: async () => {
        try {
          await configMap[props.accountType].deleteAccount({
            bizId: window.PROJECT_CONFIG.BIZ_ID,
            account_id: row.account.account_id,
            account_type: props.accountType,
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


  const handleShowCreateRule = (row: PermissionRule, e: PointerEvent) => {
    e.stopPropagation();
    ruleState.rowData = {} as PermissionRuleInfo;
    ruleState.accountId = row.account.account_id;
    ruleState.isShow = true;
  };

  const handleShowEditRule = (e: PointerEvent, row: PermissionRule, index: number) => {
    e.stopPropagation();
    ruleState.accountId = row.account.account_id;
    ruleState.rowData = row.rules[index];
    ruleState.isShow = true;
  };


  const handleShowAuthorize = (row: PermissionRule, rule: PermissionRuleInfo, e: PointerEvent) => {
    e.stopPropagation();
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
    authorizeState.rules = [rule];
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
