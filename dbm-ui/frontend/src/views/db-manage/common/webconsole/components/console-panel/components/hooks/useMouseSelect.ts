export function useMouseSelect() {
  /**
   * 触发点击
   */
  const isMouseClick = ref(false);
  /**
   * 是否在拖动中
   */
  const isMouseMoving = ref(false);

  const handleMouseDown = () => {
    isMouseClick.value = true;
  };

  const handleMouseUp = () => {
    isMouseClick.value = false;
  };

  const handleMouseMove = () => {
    if (isMouseClick.value) {
      isMouseMoving.value = true;
    }
  };

  onMounted(() => {
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mousemove', handleMouseMove);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('mousedown', handleMouseDown);
    window.removeEventListener('mouseup', handleMouseUp);
    window.removeEventListener('mousemove', handleMouseMove);
  });

  return {
    isMouseClick,
    isMouseMoving,
  };
}
