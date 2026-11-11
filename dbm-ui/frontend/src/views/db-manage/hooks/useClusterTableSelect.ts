import _ from 'lodash';
import { computed, ref } from 'vue';

export default <T extends { bk_host_id?: number; id: number }>() => {
  const selectedList = ref<T[]>([]);
  const selectedIdList = computed(() => selectedList.value.map((item) => item.id));
  // 实例导出使用主机 ID，集群等没有主机字段的数据不参与。
  const selectedHostIdList = computed(() =>
    _.uniq(selectedList.value.map((item) => item.bk_host_id).filter((id): id is number => typeof id === 'number')),
  );
  const isSelected = computed(() => selectedList.value.length > 0);

  const handleSelection = (data: unknown, list: T[]) => {
    selectedList.value = list;
  };

  return {
    handleSelection,
    isSelected,
    selectedHostIdList,
    selectedIdList,
    selectedList,
  };
};
