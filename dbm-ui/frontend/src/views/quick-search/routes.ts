import { registerModule } from '@router';

import { t } from '@locales/index';

export default () => {
  registerModule([
    {
      path: 'quick-search',
      name: 'QuickSearch',
      meta: {
        fullscreen: true,
        navName: t('查询结果'),
      },
      component: () => import('@views/quick-search/Index.vue'),
    },
  ]);
};
