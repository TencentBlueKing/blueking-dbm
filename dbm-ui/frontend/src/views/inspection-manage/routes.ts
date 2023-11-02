import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

export default () => [
  {
    path: 'inspection-manage',
    name: 'inspectionManage',
    component: () => import('@views/inspection-manage/Index.vue'),
    meta: {
      routeParentName: MainViewRouteNames.Platform,
      navName: t('巡检'),
      isMenu: true,
      activeMenu: 'inspectionManage',
    },
    redirect: {
      name: 'inspectionReport',
    },
    children: [
      {
        path: 'report',
        name: 'inspectionReport',
        component: () => import('@views/inspection-manage/report/Index.vue'),
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('健康报告'),
          isMenu: true,
          activeMenu: 'inspectionManage',
        },
      },
    ],
  },
];
