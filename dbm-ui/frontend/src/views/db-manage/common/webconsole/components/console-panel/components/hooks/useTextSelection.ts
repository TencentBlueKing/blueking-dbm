/**
 * 获取鼠标选中的内容
 */
export function useTextSelection() {
  /**
   * 鼠标选中的内容
   */
  const selectedText = ref('');

  const updateSelection = () => {
    // 实时获取选中的内容
    const selection = window.getSelection();
    selectedText.value = selection ? selection.toString() : '';
  };

  onMounted(() => {
    document.addEventListener('selectionchange', updateSelection); // 监听选中内容变化
  });

  onBeforeUnmount(() => {
    document.removeEventListener('selectionchange', updateSelection); // 移除监听器
  });

  return {
    selectedText,
  };
}
