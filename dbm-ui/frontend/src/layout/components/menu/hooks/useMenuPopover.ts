import tippy, { type Instance, type Props } from 'tippy.js';
import { onBeforeUnmount, onMounted, type Ref, watch } from 'vue';

/**
 * 侧栏收起时用 tippy 承载菜单浮层，展开时销毁实例
 * @param targetRef 触发浮层的元素
 * @param contentRef 浮层内容元素，创建实例时会被 tippy 接管
 * @param enabled 是否启用浮层
 */
export const useMenuPopover = (
  targetRef: Ref<HTMLElement | undefined>,
  contentRef: Ref<HTMLElement | undefined>,
  enabled: Ref<boolean>,
  tippyProps: Partial<Props>,
) => {
  let tippyIns: Instance | undefined;

  const destroy = () => {
    if (tippyIns) {
      tippyIns.destroy();
      tippyIns = undefined;
    }
  };

  const create = () => {
    destroy();

    if (!enabled.value || !targetRef.value || !contentRef.value) {
      return;
    }

    tippyIns = tippy(targetRef.value, {
      // 指定 document.body 可避免 tippy 在 interactive 模式下的无障碍告警
      appendTo: () => document.body,
      content: contentRef.value,
      delay: [100, 100],
      maxWidth: 'none',
      offset: [0, 6],
      ...tippyProps,
    });
  };

  onMounted(create);

  // 收起态切换后内容元素才会渲染出来，需等 DOM 更新完再建实例
  watch(enabled, create, {
    flush: 'post',
  });

  onBeforeUnmount(destroy);

  return {
    hide: () => tippyIns?.hide(),
  };
};
