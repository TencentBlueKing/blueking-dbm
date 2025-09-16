import { registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      path: 'dashboard-manage',
      name: 'DashboradManage',
      meta: {
        navName: t('运营数据'),
      },
      component: () => import('@views/dashboard-manage/Index.vue'),
      children: [
        {
          path: 'settings',
          name: 'DashboradSetting',
          meta: {
            navName: t('仪表盘管理'),
          },
          component: () => import('@views/dashboard-manage/settings/Index.vue'),
        },
        {
          path: 'view/:versionId?',
          name: 'DashboradView',
          meta: {
            navName: '',
          },
          component: () => import('@views/dashboard-manage/view/Index.vue'),
        },
      ],
    },
  ]);
};
