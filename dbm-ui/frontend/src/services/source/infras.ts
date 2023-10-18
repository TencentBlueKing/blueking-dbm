import http from '../http';
import type {
  HostSpec,
} from '../types/ticket';

const path = '/apis/infras';

/**
 * 服务器规格列表
 */
export const getInfrasHostSpecs = (params: { cityCode: string }) => http.get<HostSpec[]>(`${path}/cities/${params.cityCode}/host_specs/`);

export const fetchDbTypeList = function () {
  return http.get<Array<{ id: string, name: string }>>('/apis/infras/dbtype/list_db_types/');
};
