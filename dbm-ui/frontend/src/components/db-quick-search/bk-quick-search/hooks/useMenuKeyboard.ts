import type { Ref } from 'vue';

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

  // 面板隐藏有动画，隐藏中的面板依然在 DOM 上，此时不能再响应按键，否则一次按键会被多个面板处理
  const isMenuVisible = () => {
    const popBox = listRef.value?.closest('.tippy-box');
    return !popBox || popBox.getAttribute('data-state') === 'visible';
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (!isMenuVisible()) {
      return;
    }
    // enter键直接触发选中；输入法上屏的 Enter 不算选中
    if (['Enter', 'NumpadEnter'].includes(event.code) && !event.metaKey && !event.ctrlKey && !event.isComposing) {
      const activeItem = list.value[activeIndex.value];
      // 候选为空时不提交，避免把 undefined 作为选中值
      if (activeItem === undefined) {
        return;
      }
      submitCallback(activeItem, activeIndex.value);
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
      const listEl = listRef.value;
      const activeEl = listEl?.querySelector('.active') as HTMLElement | null;
      if (!listEl || !activeEl) {
        return;
      }
      // 高亮项超出列表可视区域时（含滚轮滚动后），就近滚动到刚好可见的位置
      const listRect = listEl.getBoundingClientRect();
      const activeRect = activeEl.getBoundingClientRect();
      if (activeRect.top < listRect.top) {
        listEl.scrollTop -= listRect.top - activeRect.top;
      } else if (activeRect.bottom > listRect.bottom) {
        listEl.scrollTop += activeRect.bottom - listRect.bottom;
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
