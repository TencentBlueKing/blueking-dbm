import { useRoute, useRouter } from 'vue-router';

import { useUrlSearch } from '@hooks';

import { useUserProfile } from '@stores';

import {
  URL_CLUSTER_DETAIL_ANCHOR_KEY,
  URL_CLUSTER_DETAIL_MEMO_KEY,
} from '@views/db-manage/common/cluster-details/constants';

const TABLE_VIEW_MODE_SETTING_KEY = 'CLUSTER_TABLE_VIEW_MODE';

export default function (clusterDetailRouteName: string) {
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();
  const userProfileStore = useUserProfile();

  const clusterId = ref(0);
  const isShowDetail = ref(false);

  /**
   * @param detailPanel 打开后激活的 Tab
   * @param anchor 打开后滚动定位的分组（URL_CLUSTER_DETAIL_ANCHOR_KEY 的值）
   */
  const goClusterDetail = (id: number, event: MouseEvent, detailPanel?: string, anchor?: string) => {
    if (event.ctrlKey || event.metaKey || userProfileStore.profile[TABLE_VIEW_MODE_SETTING_KEY] === 'jump') {
      const { href } = router.resolve({
        name: clusterDetailRouteName,
        params: {
          clusterId: id,
        },
        // 只在需要定位时带上 Tab 与锚点，其他入口保持原有新窗口行为
        query: anchor
          ? {
              [URL_CLUSTER_DETAIL_ANCHOR_KEY]: anchor,
              [URL_CLUSTER_DETAIL_MEMO_KEY]: detailPanel || '',
            }
          : undefined,
      });
      window.open(href);
      return true;
    }

    const query = getSearchParams();
    if (detailPanel) {
      query[URL_CLUSTER_DETAIL_MEMO_KEY] = detailPanel;
    }
    if (anchor) {
      query[URL_CLUSTER_DETAIL_ANCHOR_KEY] = anchor;
    } else {
      // __xx__ 形式的参数会跨搜索保留，未指定定位时清掉上一次残留的锚点
      delete query[URL_CLUSTER_DETAIL_ANCHOR_KEY];
    }
    clusterId.value = id;
    isShowDetail.value = true;
    router.replace({
      params: {
        clusterId: id,
      },
      query,
    });
  };

  const clusterDetailClose = () => {
    clusterId.value = 0;
    isShowDetail.value = false;
    const query = getSearchParams();
    delete query[URL_CLUSTER_DETAIL_ANCHOR_KEY];
    router.replace({
      params: {
        clusterId: 0,
      },
      query,
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
