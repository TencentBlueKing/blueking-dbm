import { useRoute, useRouter } from 'vue-router';

import { execCopy, getSelfDomain } from '@utils';

export const useClusterDetail = (
  clusterDetailRouterName: string,
  payload: {
    clusterId: number;
    domain: () => string;
  },
) => {
  const router = useRouter();
  const route = useRoute();

  const detailRouterPage = clusterDetailRouterName === (route.name as string);

  const handleCopyClusterMasterDomainAndLink = () => {
    const { href } = router.resolve({
      name: clusterDetailRouterName,
      params: {
        clusterId: payload.clusterId,
      },
    });

    execCopy(`${payload.domain()}\n${getSelfDomain()}${href}`);
  };

  const handleCopyDetailPageLink = () => {
    const { href } = router.resolve({
      name: clusterDetailRouterName,
      params: {
        clusterId: payload.clusterId,
      },
    });
    execCopy(`${getSelfDomain()}${href}`);
  };

  return {
    detailRouterPage,
    handleCopyClusterMasterDomainAndLink,
    handleCopyDetailPageLink,
  };
};
