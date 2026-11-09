import { type RouteLocationRaw, useRouter } from 'vue-router';

import { getBusinessHref } from '@utils';

export const locationUrl = (params: RouteLocationRaw, bizId?: number) => {
  const router = useRouter();

  const route = router.resolve(params);

  const href = bizId ? route.href.replace(/(\d)+/, `${bizId}`) : route.href;

  window.open(href);
};

export const useLocation = () => {
  const router = useRouter();

  return (params: RouteLocationRaw, bizId?: number) => {
    const route = router.resolve(params);
    // 只替换站点前缀之后的业务 id 段，站点前缀含数字时不会被误替换
    const href = bizId ? getBusinessHref(route.href, bizId) : route.href;

    window.open(href);
  };
};
