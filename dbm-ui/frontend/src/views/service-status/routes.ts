import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';

export default (): RouteRecordRaw[] => [
  {
    path: 'service-status',
    name: 'ServiceStatus',
    meta: {
      fullscreen: true,
      navName: t('服务状态'),
    },
    component: () => import('@views/service-status/Index.vue'),
  },
];
