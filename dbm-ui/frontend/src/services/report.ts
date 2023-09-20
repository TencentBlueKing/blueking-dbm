import http from './http';

export const getReport = function (params: Record<string, any>) {
  return http.get<{
    data: Record<string, unknown>[],
    name: string,
    title: {
      name: string,
      display_name: string,
      format: 'text'|'status'
    }[]
  }>('/apis/report/get_report/', params);
};
