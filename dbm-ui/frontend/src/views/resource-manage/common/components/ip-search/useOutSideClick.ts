import { onBeforeUnmount, onMounted } from 'vue';

export default (callback: () => void) => {
  const handeOutsideClick = (event: Event) => {
    const eventPath = event.composedPath() as HTMLElement[];

    for (const target of eventPath) {
      // if (
      //   /host-import-ip-search/.test(target.className) ||
      //   /bk-quick-search-panel-theme/.test(target.dataset?.theme ?? '')
      // ) {
      //   return;
      // }
      if (/host-import-ip-search/.test(target.className)) {
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
