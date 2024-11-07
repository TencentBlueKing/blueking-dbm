import { onBeforeUnmount, onMounted } from 'vue';

export default (callback: () => void) => {
  const handeOutsideClick = (event: Event) => {
    const eventPath = event.composedPath();
    // eslint-disable-next-line no-plusplus
    for (let i = 0; i < eventPath.length; i++) {
      const target = eventPath[i] as HTMLElement;
      if (
        /bk-vxe-table-setting-column-btn/.test(target.className) ||
        (target.dataset && /bk-vxe-table-setting-column-theme/.test(target.dataset.theme || 'null'))
      ) {
        return;
      }
    }
    callback();
  };

  onMounted(() => {
    document.body.addEventListener('click', handeOutsideClick);
  });

  onBeforeUnmount(() => {
    document.body.removeEventListener('click', handeOutsideClick);
  });
};
