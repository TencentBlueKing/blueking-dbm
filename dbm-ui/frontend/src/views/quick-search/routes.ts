import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';

export default (): RouteRecordRaw[] => [
  {
    name: 'QuickSearch',
    path: 'quick-search',
    meta: {
      navName: t('查询结果'),
      fullscreen: true,
    },
    component: () => import('@views/quick-search/Index.vue'),
  },
];
