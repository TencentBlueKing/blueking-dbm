import _ from 'lodash';
import { getCurrentInstance, onBeforeUnmount, onMounted, type Ref } from 'vue';

export default (rootRef: Ref<HTMLDivElement | null>, resizeHandleRef: Ref<HTMLDivElement | null>) => {
  const isResizeing = ref(false);

  const currentInstance = getCurrentInstance();

  const handleMousedown = (event: MouseEvent) => {
    isResizeing.value = true;

    const rootEle = rootRef.value as HTMLDivElement;
    const rootWidth = rootEle.getBoundingClientRect().width;
    const rootParentWidth = rootEle.parentElement?.getBoundingClientRect().width || window.innerWidth - 100;
    const startClientX = event.clientX;

    const handleMouseMove = _.throttle((event: MouseEvent) => {
      if (!isResizeing.value) {
        return;
      }
      const resizeWidth = Math.max(rootWidth + startClientX - event.clientX, currentInstance?.props.minWidth as number);
      const latestWidth = resizeWidth > rootParentWidth * 0.9 ? '90%' : `${Math.max(resizeWidth, 900)}px`;

      rootEle.style.width = latestWidth;
    }, 60);

    const handleMouseUp = () => {
      isResizeing.value = false;

      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.onselectstart = null;
      document.ondragstart = null;
    };

    document.onselectstart = function () {
      return false;
    };
    document.ondragstart = function () {
      return false;
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  onMounted(() => {
    resizeHandleRef.value!.addEventListener('mousedown', handleMousedown);
    const minWidth = currentInstance?.props.minWidth as number;
    const defaultOffsetLeft = currentInstance?.props.defaultOffsetLeft as number;
    const rootEle = rootRef.value as HTMLDivElement;
    const rootWidth = (document.body.querySelector('.navigation-container') as HTMLDivElement).getBoundingClientRect()
      .width;

    const defaultWidth = rootWidth - defaultOffsetLeft;
    rootEle.style.width = `${defaultWidth < minWidth ? minWidth : defaultWidth}px`;
  });

  onBeforeUnmount(() => {
    resizeHandleRef.value!.removeEventListener('mousedown', handleMousedown);
  });

  return {
    resizing: isResizeing,
  };
};
