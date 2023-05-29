import { inject } from 'vue';

import { provideKey } from '@components/stretch-layout/StretchLayout.vue';

export const useStretchLayout = () => {
  const context = inject(provideKey);
  if (!context) {
    throw new Error('useStretchLayout must be used within a StretchLayout component');
  }

  return context;
};
