import http from './http';

export const getDeviceClassList = function () {
  return http.get<string[]>('/apis/conf/system_settings/device_classes/');
};
