export const getBusinessHref = (href: string, bizId = window.PROJECT_CONFIG.BIZ_ID) =>
  href.replace(/^\/(\d+)/, `/${bizId}`);
