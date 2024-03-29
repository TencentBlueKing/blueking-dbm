import { type RouteLocationRaw, useRouter } from 'vue-router';

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
    const href = bizId ? route.href.replace(/(\d)+/, `${bizId}`) : route.href;

    window.open(href);
  };
};
