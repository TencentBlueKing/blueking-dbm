import _ from 'lodash';
import { computed, watch } from 'vue';
import { useRoute } from 'vue-router';

export default () => {
  const route = useRoute();

  const defaultRole = ref('');
  const countData = ref({
    pd: 0,
    surreal: 0,
    tikv: 0,
  });

  const list = computed(() => {
    return [
      {
        count: countData.value.surreal,
        id: 'surreal',
        name: `Surreal(${countData.value.surreal})`,
      },
      {
        count: countData.value.tikv,
        id: 'tikv',
        name: `TiKV(${countData.value.tikv})`,
      },
      {
        count: countData.value.pd,
        id: 'pd',
        name: `Pd(${countData.value.pd})`,
      },
    ];
  });

  const routeParamsStatus = String(route.params.status);
  if (routeParamsStatus && _.find(list.value, (item) => item.id === routeParamsStatus)) {
    defaultRole.value = routeParamsStatus;
  } else {
    defaultRole.value = _.find(list.value, (item) => item.count > 0)?.id ?? 'surreal';
  }

  watch(list, () => {
    if (route.params.status) {
      return;
    }
    defaultRole.value = _.find(list.value, (item) => item.count > 0)?.id ?? 'surreal';
  });

  return {
    defaultRole,
    list,
  };
};
