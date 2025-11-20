import { nextTick, onBeforeUnmount, onMounted, type Ref, ref, watch } from 'vue';

export default <T>(
  list: Ref<T[]>,
  listRef: Ref<HTMLElement | null>,
  submitCallback: (value: T, index: number) => void,
) => {
  const activeIndex = ref(0);

  watch(
    list,
    () => {
      activeIndex.value = 0;
    },
    {
      immediate: true,
    },
  );

  const handleKeyDown = (event: KeyboardEvent) => {
    // enter键直接触发选中
    if (['Enter', 'NumpadEnter'].includes(event.code) && activeIndex.value > -1 && !event.metaKey && !event.ctrlKey) {
      submitCallback(list.value[activeIndex.value]!, activeIndex.value);
      return;
    }
    // 上下键位移动选中
    if (!['ArrowDown', 'ArrowUp'].includes(event.code)) {
      return;
    }
    if (event.code === 'ArrowUp') {
      // 上移
      activeIndex.value -= 1;
    } else if (event.code === 'ArrowDown') {
      // 下移
      activeIndex.value += 1;
    }
    if (activeIndex.value >= list.value.length) {
      activeIndex.value = list.value.length - 1;
    }
    if (activeIndex.value < 0) {
      activeIndex.value = 0;
    }

    nextTick(() => {
      const wraperHeight = listRef.value!.getBoundingClientRect().height;
      const activeEl = listRef.value!.querySelector('.active') as HTMLElement;
      if (!activeEl) {
        return;
      }
      const activeOffsetTop = activeEl.offsetTop + 34;

      if (activeOffsetTop > wraperHeight) {
        // eslint-disable-next-line no-param-reassign
        listRef.value!.scrollTop = activeOffsetTop - wraperHeight + 10;
      } else if (activeOffsetTop <= 42) {
        // eslint-disable-next-line no-param-reassign
        listRef.value!.scrollTop = 0;
      }
    });
  };

  onMounted(() => {
    document.body.addEventListener('keydown', handleKeyDown);
  });

  onBeforeUnmount(() => {
    document.body.removeEventListener('keydown', handleKeyDown);
  });

  return {
    activeIndex,
  };
};
