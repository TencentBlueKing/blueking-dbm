export function useDisableTab() {
  const disableTabKey = (event: any) => {
    if (event.key === 'Tab') {
      event.preventDefault();
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', disableTabKey);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', disableTabKey);
  });
}
