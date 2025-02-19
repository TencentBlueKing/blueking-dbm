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
        :show-overflow="false"
        :show-settgings="false"
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
  import { useRequest } from 'vue-request';

  import {
    deleteAccount as deleteMongodbAccount,
    deleteAccountRule as deleteMongodbAccountRule,
    getPermissionRules as getMongodbPermissionRules,
  } from '@services/source/mongodbPermissionAccount';
  import {
    deleteAccount as deleteMysqlAccount,
    getPermissionRules as getMysqlPermissionRules,
  } from '@services/source/mysqlPermissionAccount';
  import {
    deleteAccount as deleteSqlserverAccount,
    getPermissionRules as getSqlserverPermissionRules,
  } from '@services/source/sqlserverPermissionAccount';
  import { createTicket } from '@services/source/ticket';
  import type { PermissionRule, PermissionRuleInfo } from '@services/types/permission';

  import { useTicketCloneInfo, useTicketMessage } from '@hooks';
  import type { CloneDataHandlerMapKeys } from '@hooks/useTicketCloneInfo/generateCloneData';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import PermissionCatch from '@components/apply-permission/Catch.vue';
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
    DELETE_RULE = 'deleteRule',
    EDIT_RULE = 'editRule',
  }

  /**
   * 配置
   * ticketType 单据类型
   * clusterTypes 集群类型
   * dbOperations 权限配置
   * ddlSensitiveWords 敏感词
   * dataSource 数据源
   * createRuleComponent 创建规则组件
   */
  const configMap = {
    [AccountTypes.MONGODB]: {
      buttonController: {
        [ButtonTypes.DELETE_RULE]: true,
        [ButtonTypes.EDIT_RULE]: false,
      },
      clusterTypes: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
      createRuleComponent: MongoCreateRule,
      dataSource: getMongodbPermissionRules,
      dbOperations: mongoDbOperations,
      ddlSensitiveWords: [],
      ticketType: TicketTypes.MONGODB_AUTHORIZE_RULES,
    },
    [AccountTypes.MYSQL]: {
      buttonController: {
        [ButtonTypes.DELETE_RULE]: true,
        [ButtonTypes.EDIT_RULE]: true,
      },
      clusterTypes: [ClusterTypes.TENDBHA, 'tendbhaSlave', ClusterTypes.TENDBSINGLE],
      createRuleComponent: MysqlCreateRule,
      dataSource: getMysqlPermissionRules,
      dbOperations: mysqlDbOperations[AccountTypes.MYSQL].dbOperations,
      ddlSensitiveWords: mysqlDbOperations[AccountTypes.MYSQL].ddlSensitiveWords,
      ticketType: TicketTypes.MYSQL_AUTHORIZE_RULES,
    },
    [AccountTypes.SQLSERVER]: {
      buttonController: {
        [ButtonTypes.DELETE_RULE]: false,
        [ButtonTypes.EDIT_RULE]: false,
      },
      clusterTypes: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
      createRuleComponent: SqlserverCreateRule,
      dataSource: getSqlserverPermissionRules,
      dbOperations: sqlserverDbOperations,
      ddlSensitiveWords: [],
      ticketType: TicketTypes.SQLSERVER_AUTHORIZE_RULES,
    },
    [AccountTypes.TENDBCLUSTER]: {
      buttonController: {
        [ButtonTypes.DELETE_RULE]: true,
        [ButtonTypes.EDIT_RULE]: true,
      },
      clusterTypes: [ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave'],
      createRuleComponent: MysqlCreateRule,
      dataSource: getMysqlPermissionRules,
      dbOperations: mysqlDbOperations[AccountTypes.TENDBCLUSTER].dbOperations,
      ddlSensitiveWords: mysqlDbOperations[AccountTypes.TENDBCLUSTER].ddlSensitiveWords,
      ticketType: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    },
  };

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  useTicketCloneInfo({
    onSuccess(cloneData) {
      const { clusterList, clusterType, dbs, sourceIpList, user } = cloneData;
      authorizeState.isShow = true;
      authorizeState.dbs = dbs;
      authorizeState.user = user;
      clusterAuthorizeRef.value!.init({
        clusterList,
        clusterType,
        sourceIpList,
      });
      window.changeConfirm = true;
    },
    type: configMap[props.accountType].ticketType as CloneDataHandlerMapKeys,
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tableSearch = ref([]);
  const clusterAuthorizeRef = ref<InstanceType<typeof ClusterAuthorize>>();
  /**
   * 集群授权
   */
  const authorizeState = reactive({
    dbs: [] as string[],
    isShow: false,
    rules: [] as PermissionRule['rules'],
    user: '',
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
    accountId: -1,
    isShow: false,
    rowData: {} as PermissionRuleInfo,
  });
  const rowExpandMap = shallowRef<Record<number, boolean>>({});

  /**
   * ddl敏感词
   */
  const ddlSensitiveWordsMap = computed(() =>
    configMap[props.accountType].ddlSensitiveWords.reduce<Record<string, boolean>>((acc, item) => {
      acc[item] = true;
      return acc;
    }, {}),
  );

  const skipApproval = computed(() => props.accountType === AccountTypes.MONGODB);

  /**
   * search select 过滤参数
   */
  const filters = [
    {
      id: 'user',
      name: t('账号名称'),
    },
    {
      id: 'access_db',
      name: t('DB名称'),
    },
    {
      children: Object.values(configMap[props.accountType].dbOperations).reduce<
        {
          id: string;
          name: string;
        }[]
      >((acc, item) => {
        acc.push(...item.map((id) => ({ id: id.toLowerCase(), name: id })));
        return acc;
      }, []),
      id: 'privilege',
      logical: '&',
      multiple: true,
      name: t('权限'),
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
      field: 'user',
      fixed: 'left',
      label: t('账号名称'),
      minWidth: 200,
      render: ({ data }: { data: PermissionRule }) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <>
                {isNewUser(data) && (
                  <bk-tag
                    class='ml-4'
                    size='small'
                    theme='success'>
                    NEW
                  </bk-tag>
                )}
                <auth-button
                  action-id='mysql_add_account_rule'
                  class='add-rule-btn'
                  permission={data.permission.mysql_add_account_rule}
                  resource={data.account.account_id}
                  size='small'
                  onClick={(event: PointerEvent) => handleShowCreateRule(data, event)}>
                  {t('添加授权规则')}
                </auth-button>
              </>
            ),
            default: () => (
              <bk-button
                theme='primary'
                text
                onClick={(event: MouseEvent) => handleViewAccount(data, event)}>
                {data.account.user}
              </bk-button>
            ),
            prepend: () =>
              data.rules.length > 1 && (
                <div
                  class='row-expand-btn'
                  onClick={() => handleToggleExpand(data)}>
                  <db-icon
                    class={{
                      'expand-flag': true,
                      'is-expand': !rowExpandMap.value[data.account.account_id],
                    }}
                    type='down-shape'
                  />
                </div>
              ),
          }}
        </TextOverflowLayout>
      ),
      showOverflow: false,
    },
    {
      className: 'access-db-column',
      field: 'access_db',
      label: t('访问的DB名'),
      minWidth: 200,
      render: ({ data }: { data: PermissionRule }) => {
        if (data.rules.length === 0) {
          return (
            <div class='cell-row'>
              <span>{t('暂无规则')}，</span>
              <auth-button
                action-id={`${props.accountType}_add_account_rule`}
                permission={data.permission[`${props.accountType}_add_account_rule`]}
                resource={data.account.account_id}
                size='small'
                theme='primary'
                text
                onClick={(event: PointerEvent) => handleShowCreateRule(data, event)}>
                {t('立即新建')}
              </auth-button>
            </div>
          );
        }
        return getRenderList(data).map((rule) => (
          <div class='cell-row'>
            <bk-tag>{rule.access_db || '--'}</bk-tag>
            {rule.priv_ticket && <RenderActionTag data={rule.priv_ticket} />}
          </div>
        ));
      },
      showOverflow: false,
    },
    {
      className: 'privilege-column',
      field: 'privilege',
      label: t('权限'),
      minWidth: 250,
      render: ({ data }: { data: PermissionRule }) =>
        getRenderList(data).map((rule) => {
          const { privilege } = rule;
          const privileges = privilege.split(',');
          return (
            <div
              v-bk-tooltips={{
                content: privilege.replace(/,/g, '，'),
                disabled: privileges.length <= 10,
              }}
              class='cell-row'>
              {privileges.map((item, index) => (
                <span>
                  {index !== 0 && <span>， </span>}
                  {item}
                  {ddlSensitiveWordsMap.value[item] && (
                    <bk-tag
                      class='ml-4'
                      size='small'
                      theme='warning'>
                      {t('敏感')}
                    </bk-tag>
                  )}
                </span>
              ))}
            </div>
          );
        }),
      showOverflow: false,
    },
    {
      className: 'privilege-column',
      label: t('操作'),
      render: ({ data }: { data: PermissionRule }) => {
        if (data.rules.length === 0) {
          return (
            <div class='cell-row'>
              <auth-button
                action-id={`${props.accountType}_account_delete`}
                permission={data.permission[`${props.accountType}_account_delete`]}
                resource={data.account.account_id}
                theme='primary'
                text
                onClick={() => handleDeleteAccount(data)}>
                {t('删除账号')}
              </auth-button>
            </div>
          );
        }

        const actionMap = {
          change: t('修改'),
          delete: t('删除'),
        };

        return getRenderList(data).map((item, index) => (
          <div class='cell-row'>
            <bk-button
              theme='primary'
              text
              onClick={(event: PointerEvent) => handleShowAuthorize(data, item, event)}>
              {t('授权')}
            </bk-button>
            {configMap[props.accountType].buttonController[ButtonTypes.DELETE_RULE] && (
              <OperationBtnStatusTips
                data={{
                  operationStatusText: t('权限规则_t_任务正在进行中', {
                    t: actionMap[data.rules[index].priv_ticket?.action],
                  }),
                  operationTicketId: data.rules[index].priv_ticket?.ticket_id,
                }}
                disabled={!data.rules[index].priv_ticket}>
                {configMap[props.accountType].buttonController[ButtonTypes.EDIT_RULE] && (
                  <bk-button
                    class='ml-8'
                    disabled={Boolean(data.rules[index].priv_ticket?.ticket_id)}
                    theme='primary'
                    text
                    onClick={(event: PointerEvent) => handleShowEditRule(event, data, index)}>
                    {t('编辑')}
                  </bk-button>
                )}
              </OperationBtnStatusTips>
            )}
            {configMap[props.accountType].buttonController[ButtonTypes.DELETE_RULE] && (
              <OperationBtnStatusTips
                data={{
                  operationStatusText: t('权限规则_t_任务正在进行中', {
                    t: actionMap[data.rules[index].priv_ticket?.action],
                  }),
                  operationTicketId: data.rules[index].priv_ticket?.ticket_id,
                }}
                disabled={!data.rules[index].priv_ticket}>
                <bk-pop-confirm
                  content={
                    skipApproval.value
                      ? t('删除规则后将不能恢复，请谨慎操作')
                      : t('删除规则会创建单据，需此规则所有过往调用方审批后才执行删除。')
                  }
                  title={t('确认删除该规则？')}
                  trigger='click'
                  width='288'
                  onConfirm={() => handleDeleteRule(data, index)}>
                  <bk-button
                    class='ml-8'
                    disabled={Boolean(data.rules[index].priv_ticket?.ticket_id)}
                    theme='primary'
                    text>
                    {t('删除')}
                  </bk-button>
                </bk-pop-confirm>
              </OperationBtnStatusTips>
            )}
          </div>
        ));
      },
      showOverflow: false,
      width: 150,
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
  });

  /**
   * 删除规则（不走审批）
   */
  const { run: deleteAccountRuleRun } = useRequest(deleteMongodbAccountRule, {
    manual: true,
    onSuccess() {
      Message({
        message: t('删除成功'),
        theme: 'success',
      });
      fetchData();
    },
  });

  // 设置行样式
  const setRowClass = (row: PermissionRule) => (isNewUser(row) ? 'is-new' : '');

  const dataSource = (params: ServiceParameters<typeof getMysqlPermissionRules>) =>
    configMap[props.accountType].dataSource({
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
  const getRenderList = (data: PermissionRule) =>
    !rowExpandMap.value[data.account.account_id] ? data.rules : data.rules.slice(0, 1);

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
    const apiMap = {
      [AccountTypes.MONGODB]: deleteMongodbAccount,
      [AccountTypes.MYSQL]: deleteMysqlAccount,
      [AccountTypes.SQLSERVER]: deleteSqlserverAccount,
      [AccountTypes.TENDBCLUSTER]: deleteMysqlAccount,
    };
    InfoBox({
      content: t('即将删除账号xx_删除后将不能恢复', { name: row.account.user }),
      onConfirm: async () => {
        try {
          await apiMap[props.accountType]({
            account_id: row.account.account_id,
            account_type: props.accountType,
            bizId: window.PROJECT_CONFIG.BIZ_ID,
          });
          Message({
            message: t('成功删除账号'),
            theme: 'success',
          });
          accountDetailDialog.isShow = false;
          fetchData();
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认删除该账号'),
      type: 'warning',
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
  const handleDeleteRule = (row: PermissionRule, index: number) => {
    if (skipApproval.value) {
      deleteAccountRuleRun({
        account_id: row.account.account_id,
        account_type: props.accountType,
        rule_id: row.rules[index].rule_id,
      });
      return;
    }
    const ticketTypeMap = {
      [AccountTypes.MYSQL]: TicketTypes.MYSQL_ACCOUNT_RULE_CHANGE,
      [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_ACCOUNT_RULE_CHANGE,
    };
    createTicketRun({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details: {
        account_id: row.account.account_id,
        account_type: props.accountType,
        action: 'delete',
        last_account_rules: {
          userName: row.account.user,
          ...row.rules[index],
        },
        rule_id: row.rules[index].rule_id,
      },
      remark: '',
      ticket_type: ticketTypeMap[props.accountType as AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER],
    });
  };
</script>

<style lang="less">
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

    .rules-table {
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

      .cell-row {
        height: 40px;
        padding: 0 16px;
        overflow: hidden;
        line-height: 40px;
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

      .access-db-column,
      .privilege-column {
        .vxe-cell {
          padding-right: 0 !important;
          padding-left: 0 !important;
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
