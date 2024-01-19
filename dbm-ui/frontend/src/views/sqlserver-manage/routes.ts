import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';
const routes: RouteRecordRaw[] = [
  {
    name: 'SqlserverManage',
    path: 'sqlServer-manage',
    children: [
      {
        name: 'SqlserverHaClusterList',
        path: 'sqlServer-ha-cluster-list',
        meta: {
          navName: t('SQLServer主从集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/ha-cluster-list/Index.vue'),
      },
      {
        name: 'Sqlserversingle',
        path: 'sqlServer-single',
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
