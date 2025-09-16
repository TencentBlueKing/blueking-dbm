import http from '../http';

export const getAppShareList = () => {
  // https://s-dbm.woa.com/bkvision/api/v1/share/get_app_share_list/
  return http.get<{ name: string; uid: string }[]>(
    'bkvision/api/v1/share/get_app_share_list/',
    {},
    {
      cache: 1000,
    },
  );
};
