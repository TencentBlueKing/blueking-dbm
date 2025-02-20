import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';

export default (): RouteRecordRaw[] => [
  {
    path: 'quick-search',
    name: 'QuickSearch',
    meta: {
      fullscreen: true,
      navName: t('查询结果'),
    },
    component: () => import('@views/quick-search/Index.vue'),
  },
];
