import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'SqlServerManage',
    path: 'sqlserver-manage',
    children: [
      {
        name: 'SqlServerHaClusterList',
        path: 'sqlserver-ha-cluster-list',
        meta: {
          navName: t('SQLServer主从集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/ha-cluster-list/Index.vue'),
      },
      {
        name: 'SqlServerHaInstanceList',
        path: 'sqlserver-ha-instance-list',
        meta: {
          navName: t('【SQLServer 主从集群】实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/ha-instance-list/Index.vue'),
      },
      {
        name: 'SqlServerSingle',
        path: 'sqlserver-single',
        meta: {
          navName: t('SQLServer单节点集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/single-cluster/Index.vue'),
      },
      {
        name: 'SqlServerPermissionRules',
        path: 'permission-rules',
        meta: {
          navName: t('授权规则'),
        },
        component: () => import('@views/sqlserver-manage/permission/Index.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return routes;
}
