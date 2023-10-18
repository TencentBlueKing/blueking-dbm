import axios from 'axios';
import Cookies from 'js-cookie';

import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import QuerySemanticExecuteResultModel from '@services/model/sql-import/query-semantic-execute-result';
import SemanticCheckResultModel from '@services/model/sql-import/semantic-check-result';
import SemanticDataModel from '@services/model/sql-import/semantic-data';
import UserSemanticTaskModel from '@services/model/sql-import/user-semantic-task';

import http from '../http';

import { useGlobalBizs } from '@/stores';

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/sql_import`;

/**
 * 删除用户语义检查任务列表
 */
export const deleteUserSemanticTasks = (params: {
  bk_biz_id: number,
  task_ids: string[],
  cluster_type: string,
}) => http.delete<number>(`${path}/delete_user_semantic_tasks/`, params);

/**
 * 获取用户语义检查任务列表
 */
export const getUserSemanticTasks = (params: {
  bk_biz_id: number,
  cluster_type?: string
}) => {
  const realParams = { ...params } as Record<string, any>;
  delete realParams.bk_biz_id;

  return http.get<UserSemanticTaskModel[]>(`${path}/get_user_semantic_tasks/`, realParams)
    .then(data => data.map(item => new UserSemanticTaskModel(item)));
};

/**
 * sql 语法检测
 */
export const grammarCheck = (params: {
  bk_biz_id: number,
  body: FormData
}) => axios({
  baseURL: window.PROJECT_ENV.VITE_AJAX_URL_PREFIX,
  url: `${path}/grammar_check/`,
  method: 'POST',
  data: params.body,
  timeout: 60000,
  headers: {
    'X-CSRFToken': Cookies.get('dbm_csrftoken'),
  },
  withCredentials: true,
}).then((data) => {
  if (data.data.code !== 0) {
    throw new Error(data.data.message);
  }
  return data.data.data;
})
  .then(data => Object.keys(data).reduce((result, key) => ({
    ...result,
    [key]: new GrammarCheckModel(data[key]),
  }), {} as Record<string, GrammarCheckModel>));

/**
 * 查询语义执行的数据
 */
export const querySemanticData = (params: {
  bk_biz_id: number,
  root_id: string
}) => http.post<QuerySemanticExecuteResultModel>(`${path}/query_semantic_data/`, params)
  .then(data => ({
    ...data,
    semantic_data: new SemanticDataModel(data.semantic_data),
  }));

/**
 * 终止语义检测流程
 */
export const revokeSemanticCheck = (params: {
  bk_biz_id: number,
  root_id: string
}) => http.post(`${path}/revoke_semantic_check/`, params);

/**
 * sql 语义检测
 */
export const semanticCheck = (params: {
  bk_biz_id: number,
  cluster_type: string
}) => http.post<SemanticCheckResultModel>(`${path}/semantic_check/`, params);
