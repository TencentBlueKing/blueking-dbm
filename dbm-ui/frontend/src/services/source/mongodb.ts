
import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();
const path = `/apis/mongodb/bizs/${currentBizId}/mongodb_replicaset_resources`;


/**
 * 导出实例数据为 excel 文件
 */
export function exportMongodbInstanceToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
