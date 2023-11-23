import {
  onMounted,
  type Ref,
  ref } from 'vue';

export const useMenuStyles = (menuBox: Ref<HTMLElement|undefined>) => {
  const style = ref({});

  onMounted(() => {
    if (!menuBox?.value) {
      return;
    }
    const { top } = menuBox.value.getBoundingClientRect();
    style.value = {
      height: `calc(100% - ${top - 52}px)`,
    };
  });
  return style;
};
