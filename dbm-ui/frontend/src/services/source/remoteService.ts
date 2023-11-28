import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/remote_service`;

/**
 * 校验DB是否在集群内
 */
export function checkClusterDatabase(params: {
  infos: Array<{
    cluster_id: number,
    db_names: string[],
  }>
}) {
  return http.post<{
    cluster_id: number,
    db_names: string[],
    check_info: Record<string, boolean>
  }[]>(`${path}/check_cluster_database/`, params);
}

/**
 * 校验flashback信息是否合法
 */
export function checkFlashbackDatabase(params: {
  infos: Array<{
    cluster_id: number,
    databases: string[],
    databases_ignore: string[],
    tables: string[],
    tables_ignore: string[]
  }>
}) {
  return http.post<{
    cluster_id: number,
    databases: string[],
    databases_ignore: string[],
    message: string,
    tables: string[],
    tables_ignore: string[]
  }[]>(`${path}/check_flashback_database/`, params);
}

/**
 * 查询集群数据库列表
 */
export function getClusterDatabaseNameList(params: {
  cluster_ids: Array<number>
}) {
  return http.post<Array<{
    cluster_id: number,
    databases: Array<string>,
    system_databases: Array<string>
  }>>(`${path}/show_cluster_databases/`, params);
}

// 查询集群数据表列表
export function getClusterTablesNameList(params: {
  cluster_db_infos: {
    cluster_id: number,
    dbs: string[],
  }[]
}) {
  return http.post<{
    cluster_id: number,
    table_data: Record<string, string[]>
  }[]>(`${path}/show_cluster_tables/`, params);
}
