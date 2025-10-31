import { useRoute, useRouter } from 'vue-router';

import { useUrlSearch } from '@hooks';

import { useUserProfile } from '@stores';

const TABLE_VIEW_MODE_SETTING_KEY = 'CLUSTER_TABLE_VIEW_MODE';

export default function (clusterDetailRouteName: string) {
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();
  const userProfileStore = useUserProfile();

  const clusterId = ref(0);
  const isShowDetail = ref(false);

  const goClusterDetail = (id: number, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey || userProfileStore.profile[TABLE_VIEW_MODE_SETTING_KEY] === 'jump') {
      const { href } = router.resolve({
        name: clusterDetailRouteName,
        params: {
          clusterId: id,
        },
      });
      window.open(href);
      return true;
    }

    clusterId.value = id;
    isShowDetail.value = true;
    router.replace({
      params: {
        clusterId: id,
      },
      query: getSearchParams(),
    });
  };

  const clusterDetailClose = () => {
    clusterId.value = 0;
    isShowDetail.value = false;
    router.replace({
      params: {
        clusterId: 0,
      },
      query: getSearchParams(),
    });
  };

  onMounted(() => {
    if (Number(route.params.clusterId)) {
      clusterId.value = Number(route.params.clusterId);
      isShowDetail.value = true;
    }
  });

  return {
    clusterDetailClose,
    clusterId,
    goClusterDetail,
    showDetail: isShowDetail,
  };
}
