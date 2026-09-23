import type { Ref } from 'vue';

/**
 * 点击组件外部时执行回调
 * @param rootRef 传入实例根节点后只以该节点为界，避免同页面多个搜索组件互相影响
 */
export default (callback: () => void, rootRef?: Ref<HTMLElement | undefined>) => {
  const isInsideClick = (target: HTMLElement) => {
    // 下拉面板挂载在 body 上，通过主题标识判断
    if (/bk-quick-search-panel-theme/.test(target.dataset?.theme ?? '')) {
      return true;
    }
    if (rootRef) {
      return target === rootRef.value;
    }
    return /bk-quick-search/.test(target.className);
  };

  const handleOutsideClick = (event: Event) => {
    const eventPath = event.composedPath() as HTMLElement[];

    for (const target of eventPath) {
      if (isInsideClick(target)) {
        return;
      }
    }

    callback();
  };

  // 捕获阶段监听：搜索框 wrapper 的点击会 stopPropagation，冒泡阶段收不到其它搜索框实例内的点击
  onMounted(() => {
    document.body.addEventListener('click', handleOutsideClick, true);
  });

  onBeforeUnmount(() => {
    document.body.removeEventListener('click', handleOutsideClick, true);
  });
};
