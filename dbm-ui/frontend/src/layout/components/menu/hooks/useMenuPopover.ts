import tippy, { type Instance, type Props } from 'tippy.js';
import { onBeforeUnmount, onMounted, type Ref, watch } from 'vue';

/**
 * 侧栏收起时用 tippy 承载菜单浮层，展开时销毁实例
 * @param targetRef 触发浮层的元素
 * @param enabled 是否启用浮层
 * @returns container 浮层内容容器，内容需通过 Teleport 渲染进去
 */
export const useMenuPopover = (
  targetRef: Ref<HTMLElement | undefined>,
  enabled: Ref<boolean>,
  tippyProps: Partial<Props>,
) => {
  // 容器由 hook 自己创建，tippy 只搬动这个不受 Vue 管理的节点，
  // 否则 tippy 把 Vue 渲染的元素移入浮层后，Vue 切换 v-if 分支会把新节点挂进浮层里
  const container = document.createElement('div');

  let tippyIns: Instance | undefined;

  const destroy = () => {
    if (tippyIns) {
      tippyIns.destroy();
      tippyIns = undefined;
    }
  };

  const create = () => {
    destroy();

    if (!enabled.value || !targetRef.value) {
      return;
    }

    tippyIns = tippy(targetRef.value, {
      // 指定 document.body 可避免 tippy 在 interactive 模式下的无障碍告警
      appendTo: () => document.body,
      content: container,
      delay: [100, 100],
      maxWidth: 'none',
      offset: [0, 6],
      ...tippyProps,
    });
  };

  onMounted(create);

  // 等 Teleport 把浮层内容渲染进容器后再建实例
  watch(enabled, create, {
    flush: 'post',
  });

  onBeforeUnmount(destroy);

  return {
    container,
    hide: () => tippyIns?.hide(),
  };
};
