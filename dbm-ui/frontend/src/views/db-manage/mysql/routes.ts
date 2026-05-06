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

import { AccountTypes, DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.MYSQL);

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  createRouteItem(TicketTypes.MYSQL_IMPORT_SQLFILE, t('变更SQL执行'), {}, { params: '/:step?' }),
  createRouteItem(TicketTypes.MYSQL_RENAME_DATABASE, t('DB重命名')),
  createRouteItem(TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, t('重建从库')),
  createRouteItem(TicketTypes.MYSQL_RESTORE_SLAVE, t('重建从库')),
  createRouteItem(TicketTypes.MYSQL_ADD_SLAVE, t('添加从库')),
  createRouteItem(TicketTypes.MYSQL_MIGRATE_CLUSTER, t('迁移主从')),
  createRouteItem(TicketTypes.MYSQL_MASTER_SLAVE_SWITCH, t('主从互切')),
  createRouteItem(TicketTypes.MYSQL_PROXY_ADD, t('添加 Proxy')),
  createRouteItem(TicketTypes.MYSQL_PROXY_REDUCE, t('减少 Proxy')),
  createRouteItem(TicketTypes.MYSQL_PROXY_CONF_CHANGE, t('Proxy 升降配')),
  createRouteItem(TicketTypes.MYSQL_PROXY_SWITCH, t('替换 Proxy')),
  createRouteItem(TicketTypes.MYSQL_PROXY_MIGRATE, t('迁移 Proxy (按集群)')),
  createRouteItem(TicketTypes.MYSQL_PROXY_MIGRATE_INS, t('迁移 Proxy (按实例)')),
  createRouteItem(TicketTypes.MYSQL_MASTER_FAIL_OVER, t('主库故障切换')),
  createRouteItem(TicketTypes.MYSQL_INSTANCE_FAIL_OVER, t('主库故障切换')),
  createRouteItem(TicketTypes.MYSQL_HA_DB_TABLE_BACKUP, t('库表备份')),
  createRouteItem(TicketTypes.MYSQL_HA_FULL_BACKUP, t('全库备份')),
  createRouteItem(TicketTypes.MYSQL_HA_TRUNCATE_DATA, t('清档')),
  createRouteItem(TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA, t('清档')),
  createRouteItem(TicketTypes.MYSQL_ROLLBACK_CLUSTER, t('定点构造')),
  createRouteItem(TicketTypes.MYSQL_CHECKSUM, t('数据校验修复')),
  createRouteItem(TicketTypes.MYSQL_CLIENT_CLONE_RULES, t('客户端权限克隆')),
  createRouteItem(TicketTypes.MYSQL_INSTANCE_CLONE_RULES, t('DB实例权限克隆')),
  createRouteItem(TicketTypes.MYSQL_DATA_MIGRATE, t('DB 数据克隆')),
  createRouteItem(TicketTypes.MYSQL_PROXY_UPGRADE, t('版本升级')),
  createRouteItem(TicketTypes.MYSQL_CLUSTER_STANDARDIZE, t('集群标准化')),
  createRouteItem(TicketTypes.MYSQL_FLASHBACK, t('回档')),
  createRouteItem(TicketTypes.MYSQL_ROLLBACK, t('回档')),
  createRouteItem(TicketTypes.MYSQL_MIGRATE_SINGLE, t('单节点迁移')),
  createRouteItem(TicketTypes.MYSQL_OPEN_AREA, t('开区模版')),
  {
    path: 'webconsole',
    name: 'MySQLWebconsole',
    meta: {
      navName: 'Webconsole',
    },
    component: () => import('@views/db-manage/mysql/webconsole/Index.vue'),
  },
  {
    path: 'merge-disk-space',
    name: 'MySQLMergeDiskSpace',
    meta: {
      navName: t('DB 数据合并空间评估'),
    },
    component: () => import('@views/db-manage/mysql/merge-disk-space/Index.vue'),
  },
  createRouteItem(TicketTypes.MYSQL_PROXY_UPGRADE, t('版本升级')), // 接入层升级
  createRouteItem(TicketTypes.MYSQL_LOCAL_UPGRADE, t('版本升级')), // 主从/单节点-存储层-本地升级
  createRouteItem(TicketTypes.MYSQL_MIGRATE_UPGRADE, t('版本升级')), // 主从-存储层-迁移升级
  createRouteItem(TicketTypes.MYSQL_CLUSTER_STANDARDIZE, t('集群标准化')),
  createRouteItem(TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER, t('构造')),
  createRouteItem(TicketTypes.MYSQL_FIXPOINT_NEW_CLUSTER, t('构造')),
];

const singleRoutes: RouteRecordRaw[] = [
  {
    path: 'tendbsingle',
    name: 'tendbsingle',
    meta: {
      navName: t('MySQL单节点_集群管理'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'DatabaseTendbsingle',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'list/:clusterId?',
        name: 'DatabaseTendbsingle',
        meta: {
          navName: t('MySQL单节点_集群管理'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/mysql/single-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'tendbsingleDetail',
        meta: {
          fullscreen: true,
          navName: t('MySQL单节点_集群详情'),
        },
        component: () => import('@views/db-manage/mysql/single-cluster-detail/Index.vue'),
      },
    ],
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    path: 'tendbha',
    name: 'tendbha',
    meta: {
      navName: t('MySQL主从集群_集群管理'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'list/:clusterId?',
        name: 'DatabaseTendbha',
        meta: {
          navName: t('MySQL主从集群_集群管理'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/mysql/ha-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'tendbHaDetail',
        meta: {
          fullscreen: true,
          navName: t('MySQL主从集群_集群详情'),
        },
        component: () => import('@views/db-manage/mysql/ha-cluster-detail/Index.vue'),
      },
      {
        path: 'instance-list',
        name: 'DatabaseTendbhaInstance',
        meta: {
          navName: t('MySQL主从集群_实例视图'),
        },
        component: () => import('@views/db-manage/mysql/ha-instance-list/Index.vue'),
      },
    ],
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    path: 'toolbox',
    name: 'MySQLToolbox',
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    redirect: {
      name: TicketTypes.MYSQL_IMPORT_SQLFILE,
    },
    component: () => import('@views/db-manage/mysql/toolbox/IndexNew.vue'),
    children: [...mysqlToolboxChildrenRouters],
  },
];

const dumperDataSubscription = {
  path: 'dumper-data-subscribe/:dumperId(\\d+)?',
  name: 'DumperDataSubscription',
  meta: {
    fullscreen: true,
    navName: t('数据订阅'),
  },
  component: () => import('@views/db-manage/mysql/dumper/Index.vue'),
};

const commonRouters: RouteRecordRaw[] = [
  {
    path: 'mysql',
    name: 'MysqlManage',
    meta: {
      dbType: DBTypes.MYSQL,
      navName: t('Mysql 集群管理'),
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'permission-rules',
        name: 'PermissionRules',
        meta: {
          navName: t('【MySQL】授权规则'),
        },
        component: () => import('@views/db-manage/mysql/permission/Index.vue'),
      },
      {
        path: 'permission-retrieve',
        name: 'MysqlPermissionRetrieve',
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
        component: () => import('@views/db-manage/mysql/MYSQL_OPEN_AREA/template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'MySQLOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/db-manage/mysql/MYSQL_OPEN_AREA/template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'MySQLOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/db-manage/mysql/MYSQL_OPEN_AREA/create/Index.vue'),
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
