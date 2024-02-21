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
        name: 'SqlServerSingle',
        path: 'sqlserver-single',
        meta: {
          navName: t('SQLServer单节点集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/single-cluster/Index.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return routes;
}
