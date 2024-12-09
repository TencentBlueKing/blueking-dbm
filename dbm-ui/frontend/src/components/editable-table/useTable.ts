import { inject } from 'vue';

import { tableInjectKey } from './Index.vue';

export default () => {
  const tableContext = inject(tableInjectKey);

  return tableContext;
};
