import _ from 'lodash';
import { onBeforeUnmount, onMounted, type Ref, shallowRef } from 'vue';

export default function (tableContentRef: Ref<HTMLElement | undefined>) {
  const leftFixedStyles = shallowRef({});
  const rightFixedStyles = shallowRef({});

  const handleHorizontalScroll = _.throttle(() => {
    const tableEl = tableContentRef.value as HTMLElement;
    const { scrollLeft } = tableEl;
    const tableContentWidth = tableEl.getBoundingClientRect().width;
    const tableWidth = tableEl.querySelector('table')!.getBoundingClientRect().width;
    if (scrollLeft === 0) {
      leftFixedStyles.value = {
        display: 'none',
      };
    } else {
      const fixedColumns = tableEl.querySelectorAll('th.is-column-fixed-left');
      const fixedWidth = Array.from(fixedColumns).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );
      leftFixedStyles.value = {
        width: `${fixedWidth}px`,
      };
    }

    if (tableContentWidth + scrollLeft >= tableWidth) {
      rightFixedStyles.value = {
        display: 'none',
      };
    } else {
      const fixedRightColumns = tableEl.querySelectorAll('th.is-column-fixed-right');
      const fixeRightdWidth = Array.from(fixedRightColumns).reduce(
        (result, itemEl) => result + itemEl.getBoundingClientRect().width,
        0,
      );
      rightFixedStyles.value = {
        width: `${fixeRightdWidth}px`,
      };
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
    initalScroll: handleHorizontalScroll,
  };
}
