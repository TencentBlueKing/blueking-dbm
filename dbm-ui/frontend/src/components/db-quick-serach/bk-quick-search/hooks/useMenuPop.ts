import tippy, { type Instance, type SingleTarget } from 'tippy.js';
import { onMounted, type Ref, ref } from 'vue';

import useOutSideClick from './useOutSideClick';

let singleMenuPop:
  | {
      hide: () => void;
      isShow: Ref<boolean>;
      popInstance?: Instance;
      show: () => void;
    }
  | undefined;

export const update = () => {
  singleMenuPop?.hide();
  setTimeout(() => {
    if (singleMenuPop && singleMenuPop.popInstance) {
      singleMenuPop.popInstance.show();
    }
  });
};

export const hideAll = () => {
  singleMenuPop?.hide();
};

export default (
  singleTarget: Ref<HTMLElement | null>,
  popContent: Ref<HTMLElement | null>,
  options = {} as {
    hideCallback?: () => void;
    showCallback?: () => void;
  },
) => {
  const isShow = ref(false);

  let popInstance: Instance;

  const show = () => {
    if (singleMenuPop && singleMenuPop.popInstance !== popInstance) {
      singleMenuPop.hide();
    }

    popInstance.show();
  };

  const hide = () => {
    popInstance.state.isVisible && popInstance.hide();
  };

  const currentMenuPop: typeof singleMenuPop = {
    hide,
    isShow,
    popInstance: undefined,
    show,
  };

  useOutSideClick(() => {
    hide();
  });

  onMounted(() => {
    popInstance = tippy(singleTarget.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: false,
      content: popContent.value as HTMLElement,
      hideOnClick: false,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 6],
      onHidden() {
        isShow.value = false;
        options.hideCallback && options.hideCallback();
      },
      onShow() {
        isShow.value = true;
      },
      onShown() {
        options.showCallback && options.showCallback();
        singleMenuPop = currentMenuPop;
      },
      placement: 'bottom-start',
      popperOptions: {
        modifiers: [
          {
            name: 'flip',
            options: {
              fallbackPlacements: ['bottom', 'bottom-end'],
            },
          },
        ],
        strategy: 'fixed',
      },
      theme: 'light bk-quick-search-type-popover',
      trigger: 'manual',
      zIndex: 9999,
    });
    currentMenuPop.popInstance = popInstance;
  });

  onBeforeUnmount(() => {
    popInstance.hide();
    popInstance.destroy();
    if (singleMenuPop === currentMenuPop) {
      singleMenuPop = undefined;
    }
  });

  return currentMenuPop;
};
