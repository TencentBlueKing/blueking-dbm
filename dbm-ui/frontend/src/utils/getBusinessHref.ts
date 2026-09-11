import { siteBasePath } from './siteBasePath';

// 传入的 href 由 router.resolve 生成，带 vue-router 的 base，业务 id 位于 base 之后
export const getBusinessHref = (href: string, bizId = window.PROJECT_CONFIG.BIZ_ID) =>
  `${siteBasePath}${href.slice(siteBasePath.length).replace(/^\/(\d+)/, `/${bizId}`)}`;
