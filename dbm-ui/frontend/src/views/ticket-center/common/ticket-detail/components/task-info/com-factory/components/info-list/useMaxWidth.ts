const updateQueue = new Set<() => number>();
let isUpdating = false;

const maxWidth = ref(0);

export default (rootRef: Readonly<ShallowRef<HTMLDivElement | null>>) => {
  maxWidth.value = 0;

  watch(maxWidth, () => {
    if (maxWidth) {
      const allLabelEleList = rootRef.value!.querySelectorAll('.db-ticket-info-item > .db-ticket-info-item-label');
      allLabelEleList.forEach((item) => {
        // eslint-disable-next-line no-param-reassign
        (item as HTMLDivElement).style.width = `${Math.ceil(maxWidth.value)}px`;
      });
    }
  });

  const processUpdateQueue = () => {
    let width = 0;
    updateQueue.forEach((item) => {
      width = Math.max(item(), width);
    });

    maxWidth.value = width;
    updateQueue.clear();
    isUpdating = false;
  };

  onMounted(() => {
    updateQueue.add(() => {
      let maxLabelWidth = 0;
      const allLabelEleList = rootRef.value!.querySelectorAll('.db-ticket-info-item > .db-ticket-info-item-label');
      allLabelEleList.forEach((item) => {
        maxLabelWidth = Math.max(maxLabelWidth, item.getBoundingClientRect().width);
      });
      return maxLabelWidth;
    });

    if (!isUpdating) {
      isUpdating = true;

      nextTick(() => {
        processUpdateQueue();
      });
    }
  });
};
