import { inject } from 'vue';

import { BatchEditColumnInjectKey } from './Index.vue';

export default function (type: string) {
  const context = inject(BatchEditColumnInjectKey);

  onMounted(() => {
    context?.addType(type);
  });

  onBeforeUnmount(() => {
    context?.deleteType(type);
  });
}
