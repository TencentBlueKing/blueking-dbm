import http from './http';

// 查询机型类型
export const getDeviceClassList = function () {
  return http.get<string[]>('/apis/conf/system_settings/device_classes/');
};

// 业务设置列表键值映射表
export const getBizSettingList = function (params: {
  bk_biz_id: number,
  key?: string
}) {
  return http.get<Record<string, any>>('/apis/conf/biz_settings/simple/', params);
};

// 更新业务设置列表键值
export const updateBizSetting = function (params: {
  bk_biz_id: number,
  key: string,
  value: any,
  value_type?: string,
}) {
  return http.post('/apis/conf/biz_settings/update_settings/', params);
};
