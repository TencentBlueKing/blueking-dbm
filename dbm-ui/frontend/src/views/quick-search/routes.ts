import type { RouteRecordRaw } from 'vue-router';

import { t } from '@locales/index';

export default (): RouteRecordRaw[] => [
  {
    component: () => import('@views/quick-search/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('查询结果'),
    },
    name: 'QuickSearch',
    path: 'quick-search',
  },
];
