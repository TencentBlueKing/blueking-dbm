import _ from 'lodash';
import { onBeforeUnmount, onMounted, type Ref, ref } from 'vue';

export default (
  rootEle: Ref<HTMLElement | undefined>,
  panelEle: Ref<HTMLElement | undefined>,
  inputType: 'input' | 'textarea' = 'input',
) => {
  const activeIndex = ref(-1);

  const handleKeydown = _.throttle((event: KeyboardEvent) => {
    activeIndex.value = -1;
    if (!panelEle.value) {
      return;
    }
    const resultItemElList = panelEle.value.querySelectorAll('.result-item');
    if (resultItemElList.length < 1) {
      return;
    }

    const index = _.findIndex(resultItemElList, (el) => el.classList.contains('active'));
    if (event.code === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.stopPropagation();
      if (index > -1) {
        (resultItemElList[index] as HTMLElement).click();
      }
      return;
    }

    let nextIndex = 0;

    if (event.code === 'ArrowDown') {
      nextIndex = index + 1;
      if (nextIndex >= resultItemElList.length) {
        return;
      }
    } else if (event.code === 'ArrowUp') {
      nextIndex = index - 1;
      nextIndex = Math.max(nextIndex, -1);
    } else {
      // 除上下键外，其他按键不应该选中
      return;
    }

    activeIndex.value = nextIndex;
    resultItemElList.forEach((ele) => ele.classList.remove('active'));
    if (nextIndex > -1) {
      resultItemElList[nextIndex].classList.add('active');
    }

    // 选中的自动出现视窗中
    const wraperHeight = panelEle.value.getBoundingClientRect().height;

    setTimeout(() => {
      const activeOffsetTop = (panelEle.value!.querySelector('.active') as HTMLElement).offsetTop;

      if (activeOffsetTop + 32 > wraperHeight) {
        // eslint-disable-next-line no-param-reassign
        panelEle.value!.querySelector('.scroll-faker-content')!.scrollTop = activeOffsetTop - wraperHeight + 64;
      } else if (activeOffsetTop <= 42) {
        // eslint-disable-next-line no-param-reassign
        panelEle.value!.querySelector('.scroll-faker-content')!.scrollTop = 0;
      }
    });
  }, 30);

  const handleMousemove = _.throttle((event: Event) => {
    const target = event.target as HTMLElement;
    if (target.classList.contains('result-item')) {
      const resultItemElList = panelEle.value!.querySelectorAll('.result-item');
      resultItemElList.forEach((ele) => ele.classList.remove('active'));
      target.classList.add('active');
      activeIndex.value = _.findIndex(resultItemElList, (ele) => ele === target);
    }
  }, 100);

  onMounted(() => {
    rootEle.value!.querySelector(inputType)!.addEventListener('keydown', handleKeydown);
    panelEle.value!.addEventListener('mousemove', handleMousemove);
  });

  onBeforeUnmount(() => {
    rootEle.value!.querySelector(inputType)!.removeEventListener('keydown', handleKeydown);
    panelEle.value!.removeEventListener('mousemove', handleMousemove);
  });

  return {
    activeIndex,
  };
};
