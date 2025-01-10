import _ from 'lodash';
import { onBeforeUnmount, onMounted, type Ref, shallowRef } from 'vue';

export default function (tableContentRef: Ref<HTMLElement | undefined>) {
  const leftFixedStyles = shallowRef({});
  const rightFixedStyles = shallowRef({});
  const isFixedLeft = ref(false);
  const isFixedRight = ref(false);

  const handleHorizontalScroll = _.throttle(() => {
    const tableEl = tableContentRef.value as HTMLElement;
    const { scrollLeft } = tableEl;
    const tableWrapperWidth = tableEl.getBoundingClientRect().width;
    const tableWidth = tableEl.querySelector('table')!.getBoundingClientRect().width;
    if (scrollLeft === 0) {
      leftFixedStyles.value = {
        display: 'none',
      };
      isFixedLeft.value = false;
    } else {
      const fixedWidth = Array.from(tableEl.querySelectorAll('th.fixed-left-column')).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );

      leftFixedStyles.value = {
        width: `${fixedWidth}px`,
      };
      isFixedLeft.value = true;
    }
    if (tableWrapperWidth + scrollLeft >= tableWidth) {
      rightFixedStyles.value = {
        display: 'none',
      };
      isFixedRight.value = false;
    } else {
      const fixedWidth = Array.from(tableEl.querySelectorAll('th.fixed-right-column')).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );
      rightFixedStyles.value = {
        width: `${fixedWidth}px`,
      };
      isFixedRight.value = true;
    }
  }, 30);

  onMounted(() => {
    const tableEl = tableContentRef.value as HTMLElement;
    tableEl.addEventListener('scroll', handleHorizontalScroll);
    onBeforeUnmount(() => {
      tableEl.removeEventListener('scroll', handleHorizontalScroll);
    });
  });

  return {
    leftFixedStyles,
    rightFixedStyles,
    fixedLeft: isFixedLeft,
    fixedRight: isFixedRight,
    initalScroll: handleHorizontalScroll,
  };
}
