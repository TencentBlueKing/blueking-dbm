import { computed, ref } from 'vue';

export default <T extends { id: number }>() => {
  const selectedList = ref<T[]>([]);
  const selectedIdList = computed(() => selectedList.value.map((item) => item.id));
  const isSelected = computed(() => selectedList.value.length > 0);

  const handleSelection = (data: unknown, list: T[]) => {
    selectedList.value = list;
  };

  return {
    handleSelection,
    isSelected,
    selectedIdList,
    selectedList,
  };
};
