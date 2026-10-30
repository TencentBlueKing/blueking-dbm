import { computed, type UnwrapRef } from 'vue';

export default () => {
  const defaultRole = ref('vminsert');
  const countData = ref({
    vminsert: 0,
    vmselect: 0,
    vmstorage: 0,
  });

  const list = computed(() => {
    return [
      {
        count: countData.value.vminsert,
        id: 'vminsert',
        name: `vminsert(${countData.value.vminsert})`,
      },
      {
        count: countData.value.vmselect,
        id: 'vmselect',
        name: `vmselect(${countData.value.vmselect})`,
      },
      {
        count: countData.value.vmstorage,
        id: 'vmstorage',
        name: `vmstorage(${countData.value.vmstorage})`,
      },
    ];
  });

  const changeCountData = (data: UnwrapRef<typeof countData>) => {
    countData.value = data;
  };

  return {
    changeCountData,
    defaultRole,
    list,
  };
};
