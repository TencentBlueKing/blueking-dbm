import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import SemanticCheckResultModel from '@services/model/sql-import/semantic-check-result';
import SemanticDataModel from '@services/model/sql-import/semantic-data';
import UserSemanticTaskModel from '@services/model/sql-import/user-semantic-task';

import http from '../http';

// const path = `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import`;

/**
 * 删除用户语义检查任务列表
 */
export function deleteUserSemanticTasks(params: { task_ids: string[]; cluster_type: string }) {
  return http.delete<number>(
    `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/delete_user_semantic_tasks/`,
    params,
  );
}

/**
 * 获取用户语义检查任务列表
 */
export function getUserSemanticTasks(params: { cluster_type?: string }) {
  return http
    .get<
      UserSemanticTaskModel[]
    >(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/get_user_semantic_tasks/`, params)
    .then((data) => data.map((item) => new UserSemanticTaskModel(item)));
}

/**
 * sql 语法检测
 */
export function grammarCheck(params: FormData) {
  return http.post(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/grammar_check/`, params).then((data) =>
    Object.keys(data).reduce(
      (result, key) => ({
        ...result,
        [key]: new GrammarCheckModel(data[key]),
      }),
      {} as Record<string, GrammarCheckModel>,
    ),
  );
}

/**
 * 查询语义执行的数据
 */
export function querySemanticData(params: { root_id: string }) {
  return http
    .post(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/query_semantic_data/`, params)
    .then((data) => new SemanticDataModel(data));
}

/**
 * 终止语义检测流程
 */
export function revokeSemanticCheck(params: { root_id: string }) {
  return http.post(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/revoke_semantic_check/`, params);
}

/**
 * sql 语义检测
 */
export function semanticCheck(params: { cluster_type: string }) {
  return http.post<SemanticCheckResultModel>(
    `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/semantic_check/`,
    params,
  );
}

/**
 * 获取语义执行的结果日志
 */
export function semanticCheckResultLogs(params: { cluster_type: string; root_id: string; node_id: string }) {
  return http.post<
    {
      filename: string;
      match_logs: {
        timestamp: string;
        levelname: string;
        message: string;
      }[];
      status: string;
    }[]
  >(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/get_semantic_check_result_logs/`, params);
}

// 获取语义执行结果
export function getSemanticExecuteResult(params: { root_id: string }) {
  return http.post<
    {
      bill_task_id: string;
      task_id: string;
      line_id: 0;
      mysql_version: string;
      file_name_hash: string;
      file_name: string;
      status: 'Failed' | 'Success';
      err_msg: string;
      update_time: string;
      create_time: string;
      dbnames: string[];
      ignore_dbnames: string[];
    }[]
  >(`/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/get_semantic_execute_result/`, params);
}
