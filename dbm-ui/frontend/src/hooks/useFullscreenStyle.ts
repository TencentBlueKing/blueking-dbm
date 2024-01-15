import _ from 'lodash';
import {
  onBeforeUnmount,
  onMounted,
  type Ref,
  ref } from 'vue';

import { getOffset } from '@utils';

export const useFullscreenStyle = (elementRef: Ref<HTMLElement|undefined>) => {
  const style = ref({});

  onMounted(() => {
    if (!elementRef.value) {
      return;
    }
    const observer = new MutationObserver(_.throttle(() => {
      const { top } = getOffset(elementRef.value as HTMLElement);
      style.value = {
        height: `calc(100vh - ${top}px)`,
      };
    }, 100));

    observer.observe(elementRef.value, {
      subtree: true,
      childList: true,
      attributes: true,
    });

    onBeforeUnmount(() => {
      observer.takeRecords();
      observer.disconnect();
    });
  });


  return style;
};
