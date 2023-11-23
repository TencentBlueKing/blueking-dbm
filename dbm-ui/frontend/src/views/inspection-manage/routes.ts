import { t } from '@locales/index';

export default () => [
  {
    path: 'inspection-manage',
    name: 'inspectionManage',
    component: () => import('@views/inspection-manage/Index.vue'),
    meta: {
      navName: t('巡检'),
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
          navName: t('健康报告'),
          fullscreen: true,
        },
      },
    ],
  },
];
