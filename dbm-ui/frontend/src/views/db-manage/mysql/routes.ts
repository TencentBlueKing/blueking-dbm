/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import type { RouteRecordRaw } from 'vue-router';

import type { MySQLFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { AccountTypes } from '@common/const';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLExecute',
    path: 'sql-execute/:step?',
    meta: {
      navName: t('变更SQL执行'),
    },
    component: () => import('@views/db-manage/mysql/sql-execute/index.vue'),
  },
  {
    name: 'MySQLDBRename',
    path: 'db-rename/:page?',
    meta: {
      navName: t('DB重命名'),
    },
    component: () => import('@views/db-manage/mysql/db-rename/Index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneClient',
    path: 'privilege-clone-client/:page?',
    meta: {
      navName: t('客户端权限克隆'),
    },
    component: () => import('@views/db-manage/mysql/privilege-clone-client/Index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneInst',
    path: 'privilege-clone-inst/:page?',
    meta: {
      navName: t('DB实例权限克隆'),
    },
    component: () => import('@views/db-manage/mysql/privilege-clone-inst/Index.vue'),
  },
  {
    name: 'MySQLSlaveRebuild',
    path: 'slave-rebuild/:page?',
    meta: {
      navName: t('重建从库'),
    },
    component: () => import('@views/db-manage/mysql/slave-rebuild/index.vue'),
  },
  {
    name: 'MySQLSlaveAdd',
    path: 'slave-add/:page?',
    meta: {
      navName: t('添加从库'),
    },
    component: () => import('@views/db-manage/mysql/slave-add/Index.vue'),
  },
  {
    name: 'MySQLMasterSlaveClone',
    path: 'master-slave-clone/:page?',
    meta: {
      navName: t('迁移主从'),
    },
    component: () => import('@views/db-manage/mysql/master-slave-clone/index.vue'),
  },
  {
    name: 'MySQLMasterSlaveSwap',
    path: 'master-slave-swap/:page?',
    meta: {
      navName: t('主从互切'),
    },
    component: () => import('@views/db-manage/mysql/master-slave-swap/index.vue'),
  },
  {
    name: 'MySQLProxyReplace',
    path: 'proxy-replace/:page?',
    meta: {
      navName: t('替换Proxy'),
    },
    component: () => import('@views/db-manage/mysql/proxy-replace/index.vue'),
  },
  {
    name: 'MySQLProxyAdd',
    path: 'proxy-add/:page?',
    meta: {
      navName: t('添加Proxy'),
    },
    component: () => import('@views/db-manage/mysql/proxy-add/index.vue'),
  },
  {
    name: 'MySQLMasterFailover',
    path: 'master-failover/:page?',
    meta: {
      navName: t('主库故障切换'),
    },
    component: () => import('@views/db-manage/mysql/master-failover/index.vue'),
  },
  {
    name: 'MySQLDBTableBackup',
    path: 'db-table-backup/:page?',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/db-manage/mysql/db-table-backup/index.vue'),
  },
  {
    name: 'MySQLDBBackup',
    path: 'db-backup/:page?',
    meta: {
      navName: t('全库备份'),
    },
    component: () => import('@views/db-manage/mysql/db-backup/index.vue'),
  },
  {
    name: 'MySQLDBClear',
    path: 'db-clear/:page?',
    meta: {
      navName: t('清档'),
    },
    component: () => import('@views/db-manage/mysql/db-clear/Index.vue'),
  },
  {
    name: 'MySQLDBRollback',
    path: 'rollback/:page?',
    meta: {
      navName: t('定点构造'),
    },
    component: () => import('@views/db-manage/mysql/rollback/Index.vue'),
  },
  {
    name: 'MySQLDBFlashback',
    path: 'flashback/:page?',
    meta: {
      navName: t('闪回'),
    },
    component: () => import('@views/db-manage/mysql/flashback/Index.vue'),
  },
  {
    name: 'MySQLChecksum',
    path: 'checksum/:page?',
    meta: {
      navName: t('数据校验修复'),
    },
    component: () => import('@views/db-manage/mysql/checksum/Index.vue'),
  },
  {
    name: 'MySQLOpenareaTemplate',
    path: 'openarea-template',
    meta: {
      navName: t('开区模版'),
    },
    component: () => import('@views/db-manage/mysql/openarea/template/Index.vue'),
  },
  {
    name: 'MySQLDataMigrate',
    path: 'data-migrate/:page?',
    meta: {
      navName: t('DB克隆'),
    },
    component: () => import('@views/db-manage/mysql/data-migrate/Index.vue'),
  },
  {
    name: 'MySQLWebconsole',
    path: 'webconsole',
    meta: {
      navName: 'Webconsole',
    },
    component: () => import('@views/db-manage/mysql/webconsole/Index.vue'),
  },
  {
    name: 'MySQLVersionUpgrade',
    path: 'version-upgrade/:page?',
    meta: {
      navName: t('版本升级'),
    },
    component: () => import('@views/db-manage/mysql/version-upgrade/Index.vue'),
  },
  {
    name: 'MYSQL_FLASHBACK',
    path: 'MYSQL_FLASHBACK/:page?',
    meta: {
      navName: t('闪回'),
    },
    component: () => import('@views/db-manage/mysql/MYSQL_FLASHBACK/Index.vue'),
  },
];

const singleRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbsingle',
    path: 'single-cluster-list',
    meta: {
      navName: t('MySQL单节点_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/db-manage/mysql/single-cluster-list/Index.vue'),
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbha',
    path: 'ha-cluster-list',
    meta: {
      navName: t('MySQL主从集群_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/db-manage/mysql/ha-cluster-list/Index.vue'),
  },
  {
    name: 'DatabaseTendbhaInstance',
    path: 'ha-instance-list',
    meta: {
      navName: t('MySQL主从集群_实例视图'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/db-manage/mysql/ha-instance-list/Index.vue'),
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLToolbox',
    path: 'toolbox',
    redirect: {
      name: 'MySQLExecute',
    },
    meta: {
      navName: t('工具箱'),
      fullscreen: true,
    },
    component: () => import('@views/db-manage/mysql/toolbox/index.vue'),
    children: mysqlToolboxChildrenRouters,
  },
];

const dumperDataSubscription = {
  name: 'DumperDataSubscription',
  path: 'dumper-data-subscribe/:dumperId(\\d+)?',
  meta: {
    navName: t('数据订阅'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/mysql/dumper/Index.vue'),
};

const commonRouters: RouteRecordRaw[] = [
  {
    name: 'MysqlManage',
    path: 'mysql',
    meta: {
      navName: t('Mysql 集群管理'),
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        name: 'PermissionRules',
        path: 'permission-rules',
        meta: {
          navName: t('【MySQL】授权规则'),
        },
        component: () => import('@views/db-manage/mysql/permission/Index.vue'),
      },
      {
        name: 'MysqlPermissionRetrieve',
        path: 'permission-retrieve',
        meta: {
          navName: t('权限查询'),
        },
        props: { accountType: AccountTypes.MYSQL },
        component: () => import('@views/permission-retrieve/Index.vue'),
      },
      {
        path: 'whitelist',
        name: 'mysqlWhitelist',
        meta: {
          navName: t('授权白名单'),
        },
        component: () => import('@views/whitelist/list/Index.vue'),
      },
      {
        path: 'partition-manage',
        name: 'mysqlPartitionManage',
        meta: {
          navName: t('Mysql 分区管理'),
        },
        component: () => import('@views/db-manage/mysql/partition-manage/Index.vue'),
      },
      {
        path: 'openarea-template-create',
        name: 'MySQLOpenareaTemplateCreate',
        meta: {
          navName: t('新建开区模板'),
        },
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'MySQLOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'mysqlOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/db-manage/mysql/openarea/create/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  // 关闭 mysql 功能
  if (controller.mysql !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'MysqlManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (checkDbConsole('mysql.dataSubscription')) {
    commonRouters[0].children!.push(dumperDataSubscription);
  }

  if (controller.tendbsingle) {
    renderRoutes.children?.push(...singleRoutes);
  }
  if (controller.tendbha) {
    renderRoutes.children?.push(...haRoutes);
  }
  if (controller.toolbox) {
    renderRoutes.children?.push(...mysqlToolboxRouters);
  }
  return commonRouters;
}
