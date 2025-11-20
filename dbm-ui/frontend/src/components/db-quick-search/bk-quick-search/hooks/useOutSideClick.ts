import { onBeforeUnmount, onMounted } from 'vue';

export default (callback: () => void) => {
  const handeOutsideClick = (event: Event) => {
    const eventPath = event.composedPath() as HTMLElement[];

    for (const target of eventPath) {
      if (/bk-quick-search/.test(target.className) || /bk-quick-search-panel-theme/.test(target.dataset?.theme ?? '')) {
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
