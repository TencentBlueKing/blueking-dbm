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
          value-behavior="need-key"
          @change="handleSearchChange" />
      </div>
      <DbTable
        ref="tableRef"
        class="rules-table"
        :columns="columns"
        :data-source="dataSource"
        releate-url-query
        :row-class="setRowClass"
        row-hover="auto"
        @clear-search="handleClearSearch" />
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
  import { useRequest } from 'vue-request';

  import { deleteAccount as deleteMongodbAccount, getPermissionRules as getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { deleteAccount as deleteMysqlAccount, getPermissionRules as getMysqlPermissionRules } from '@services/source/mysqlPermissionAccount';
  import { deleteAccount as deleteSqlserverAccount, getPermissionRules as getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import { createTicket } from '@services/source/ticket';
  import type { PermissionRule, PermissionRuleInfo } from '@services/types/permission';

  import {
    useTicketCloneInfo,
    useTicketMessage,
  } from '@hooks';
  import type { CloneDataHandlerMapKeys } from '@hooks/useTicketCloneInfo/generateCloneData';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import PermissionCatch from '@components/apply-permission/Catch.vue'
  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import MongoCreateRule from '@views/db-manage/common/permission/components/mongo/CreateRule.vue';
  import MysqlCreateRule from '@views/db-manage/common/permission/components/mysql/create-rule/Index.vue';
  import SqlserverCreateRule from '@views/db-manage/common/permission/components/sqlserver/CreateRule.vue';

  import { getSearchSelectorParams } from '@utils';

  import AccountCreate from './components/common/AccountCreate.vue';
  import AccountDetail from './components/common/AccountDetail.vue';
  import RenderActionTag from './components/common/RenderActionTag.vue';
  import mongoDbOperations from './components/mongo/config';
  import mysqlDbOperations from './components/mysql/config';
  import sqlserverDbOperations from './components/sqlserver/config';

  interface Props {
    accountType: AccountTypes;
  }

  const props = defineProps<Props>();

  enum ButtonTypes {
    EDIT_RULE = 'editRule',
    DELETE_RULE = 'deleteRule',
  }

  /**
   * 配置
   * ticketType 单据类型
   * clusterTypes 集群类型
   * dbOperations 权限配置
   * ddlSensitiveWords 敏感词
   * dataSource 数据源
   * deleteAccount 删除账号api
   * createRuleComponent 创建规则组件
   */
  const configMap = {
    [AccountTypes.MYSQL]: {
      ticketType: TicketTypes.MYSQL_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.TENDBHA, 'tendbhaSlave', ClusterTypes.TENDBSINGLE],
      dbOperations: mysqlDbOperations[AccountTypes.MYSQL].dbOperations,
      ddlSensitiveWords: mysqlDbOperations[AccountTypes.MYSQL].ddlSensitiveWords,
      dataSource: getMysqlPermissionRules,
      deleteAccount: deleteMysqlAccount,
      createRuleComponent: MysqlCreateRule,
      buttonController: {
        [ButtonTypes.EDIT_RULE]: true,
        [ButtonTypes.DELETE_RULE]: true,
      }
    },
    [AccountTypes.TENDBCLUSTER]: {
      ticketType: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave'],
      dbOperations: mysqlDbOperations[AccountTypes.TENDBCLUSTER].dbOperations,
      ddlSensitiveWords: mysqlDbOperations[AccountTypes.TENDBCLUSTER].ddlSensitiveWords,
      dataSource: getMysqlPermissionRules,
      deleteAccount: deleteMysqlAccount,
      createRuleComponent: MysqlCreateRule,
      buttonController: {
        [ButtonTypes.EDIT_RULE]: true,
        [ButtonTypes.DELETE_RULE]: true,
      }
    },
    [AccountTypes.SQLSERVER]: {
      ticketType: TicketTypes.SQLSERVER_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
      dbOperations: sqlserverDbOperations,
      ddlSensitiveWords: [],
      dataSource: getSqlserverPermissionRules,
      deleteAccount: deleteSqlserverAccount,
      createRuleComponent: SqlserverCreateRule,
      buttonController: {
        [ButtonTypes.EDIT_RULE]: false,
        [ButtonTypes.DELETE_RULE]: false,
      }
    },
    [AccountTypes.MONGODB]: {
      ticketType: TicketTypes.MONGODB_AUTHORIZE_RULES,
      clusterTypes: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
      dbOperations: mongoDbOperations,
      ddlSensitiveWords: [],
      dataSource: getMongodbPermissionRules,
      deleteAccount: deleteMongodbAccount,
      createRuleComponent: MongoCreateRule,
      buttonController: {
        [ButtonTypes.EDIT_RULE]: false,
        [ButtonTypes.DELETE_RULE]: false,
      }
    },
  };

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

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

  /**
   * ddl敏感词
   */
  const ddlSensitiveWordsMap = computed(() => configMap[props.accountType].ddlSensitiveWords.reduce<Record<string, boolean>>((acc, item) => {
      acc[item] = true;
      return acc;
    }, {}));

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

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      showOverflowTooltip: false,
      width: 350,
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
      width: 350,
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
                { rule.priv_ticket && <RenderActionTag data={rule.priv_ticket} /> }
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
          const privileges = privilege.split(',');
          return (
            <div
              class="cell-row"
              v-bk-tooltips={{
                content: privilege.replace(/,/g, '，'),
                disabled: privileges.length <= 10,
              }}>
              {
                privileges.map((item, index) =>
                  <span>
                    {index !== 0 && <span>， </span>}
                    {item}
                    {
                      ddlSensitiveWordsMap.value[item] &&
                      <bk-tag
                        class='ml-4'
                        size='small'
                        theme='warning'>
                        {t('敏感')}
                      </bk-tag>
                    }
                  </span>
                )
              }
            </div>
          );
        })
      ),
    },
    {
      label: t('操作'),
      width: 150,
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

        const actionMap = {
          delete: t('删除'),
          change: t('修改'),
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
                <OperationBtnStatusTips
                  disabled={!data.rules[index].priv_ticket}
                  data={{
                    operationStatusText: t('权限规则_t_任务正在进行中', { t: actionMap[data.rules[index].priv_ticket?.action] }),
                    operationTicketId: data.rules[index].priv_ticket?.ticket_id,
                  }}>
                  {
                    configMap[props.accountType].buttonController[ButtonTypes.EDIT_RULE] &&
                    <bk-button
                      theme="primary"
                      class="ml-8"
                      text
                      disabled={data.rules[index].priv_ticket?.ticket_id}
                      onClick={(event: PointerEvent) => handleShowEditRule(event, data, index)}>
                      {t('编辑')}
                    </bk-button>
                  }
                  {
                    configMap[props.accountType].buttonController[ButtonTypes.DELETE_RULE] &&
                    <bk-pop-confirm
                      width="288"
                      content={t('删除规则会创建单据，需此规则所有过往调用方审批后才执行删除。')}
                      title={t('确认删除该规则？')}
                      trigger="click"
                      onConfirm={() => handleShowDeleteRule(data, index)}
                    >
                      <bk-button
                        theme="primary"
                        class="ml-8"
                        disabled={data.rules[index].priv_ticket?.ticket_id}
                        text>
                        {t('删除')}
                      </bk-button>
                    </bk-pop-confirm>
                  }
                </OperationBtnStatusTips>
              }
            </div>
          ))
        );
      },
    },
  ];

  /**
   * 规则变更走单据
   */
   const { run: createTicketRun } = useRequest(createTicket, {
    manual: true,
    onSuccess(data) {
      ticketMessage(data.id);
      fetchData();
    },
  })

  // 设置行样式
  const setRowClass = (row: PermissionRule) => (isNewUser(row) ? 'is-new' : '');

  const dataSource = (params: ServiceParameters<typeof getMysqlPermissionRules>) => configMap[props.accountType].dataSource({
    ...params,
    ...getSearchSelectorParams(tableSearch.value),
    account_type: props.accountType,
  });

  const fetchData = () => {
    tableRef.value!.fetchData();
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

  /**
   * 新建账号
   */
  const handleShowAccountDialog = () => {
    accountDialog.isShow = true;
  };

  /**
   * 浏览账号信息
   */
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

  /*
  * 授权
  */
  const handleShowAuthorize = (row: PermissionRule, rule: PermissionRuleInfo, e: PointerEvent) => {
    e.stopPropagation();
    authorizeState.isShow = true;
    authorizeState.user = row.account.user;
    authorizeState.dbs = [rule.access_db];
    authorizeState.rules = [rule];
  };

  /**
   * 创建规则
   */
  const handleShowCreateRule = (row: PermissionRule, e: PointerEvent) => {
    e.stopPropagation();
    ruleState.rowData = {} as PermissionRuleInfo;
    ruleState.accountId = row.account.account_id;
    ruleState.isShow = true;
  };

  /**
   * 编辑规则
   */
  const handleShowEditRule = (e: PointerEvent, row: PermissionRule, index: number) => {
    e.stopPropagation();
    ruleState.accountId = row.account.account_id;
    ruleState.rowData = row.rules[index];
    ruleState.isShow = true;
  };

  /**
   * 删除规则
   */
  const handleShowDeleteRule = (row: PermissionRule, index: number) => {
    const ticketTypeMap = {
      [AccountTypes.MYSQL]: TicketTypes.MYSQL_ACCOUNT_RULE_CHANGE,
      [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_ACCOUNT_RULE_CHANGE,
    }
    createTicketRun({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      ticket_type: ticketTypeMap[props.accountType as AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER],
      remark: '',
      details: {
        last_account_rules: {
          userName: row.account.user,
          ...row.rules[index],
        },
        action: 'delete',
        account_type: props.accountType,
        account_id: row.account.account_id,
        rule_id: row.rules[index].rule_id,
      },
    });
  };
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
