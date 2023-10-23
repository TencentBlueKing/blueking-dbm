import { useGlobalBizs } from '@stores';

import http from '../http';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/remote_service`;

/**
 * 校验DB是否在集群内
 */
export const checkClusterDatabase = (params: {
  infos: Array<{
    cluster_id: number,
    db_names: string[],
  }>
}) => http.post<{
    cluster_id: number,
    db_names: string[],
    check_info: Record<string, boolean>
  }[]>(`${path}/check_cluster_database/`, params);

/**
 * 校验flashback信息是否合法
 */
export const checkFlashbackDatabase = (params: {
  infos: Array<{
    cluster_id: number,
    databases: string[],
    databases_ignore: string[],
    tables: string[],
    tables_ignore: string[]
  }>
}) => http.post<{
    cluster_id: number,
    databases: string[],
    databases_ignore: string[],
    message: string,
    tables: string[],
    tables_ignore: string[]
  }[]>(`${path}/check_flashback_database/`, params);

/**
 * 查询集群数据库列表
 */
export const getClusterDBNames = (params: {
  cluster_ids: Array<number>
}) => http.post<Array<{
    cluster_id: number,
    databases: Array<string>,
    system_databases: Array<string>
  }>>(`${path}/show_cluster_databases/`, params);
