import http from './http';

export const fetchDbTypeList = function () {
  return http.get<Array<{ id: string, name: string }>>('/apis/infras/dbtype/list_db_types/');
};
