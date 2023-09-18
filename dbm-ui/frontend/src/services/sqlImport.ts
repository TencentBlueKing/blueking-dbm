/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

import axios from 'axios';
import Cookies from 'js-cookie';

import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import QuerySemanticExecuteResultModel from '@services/model/sql-import/query-semantic-execute-result';
import SemanticCheckResultModel from '@services/model/sql-import/semantic-check-result';
import SemanticDataModel from '@services/model/sql-import/semantic-data';
import UserSemanticTaskModel from '@services/model/sql-import/user-semantic-task';

import http from './http';

// sql 语法检测
export const grammarCheck = function (params: {bk_biz_id: number, body:FormData }) {
  return axios({
    baseURL: window.PROJECT_ENV.VITE_AJAX_URL_PREFIX,
    url: `/apis/mysql/bizs/${params.bk_biz_id}/sql_import/grammar_check/`,
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
};

// sql 语义检测
export const semanticCheck = function (params: {
  bk_biz_id: number,
  cluster_type: string
}) {
  return http.post<SemanticCheckResultModel>(`/apis/mysql/bizs/${params.bk_biz_id}/sql_import/semantic_check/`, params);
};

// 终止语义检测流程
export const revokeSemanticCheck = function (params: {bk_biz_id: number, root_id: string}) {
  return http.post(`/apis/mysql/bizs/${params.bk_biz_id}/sql_import/revoke_semantic_check/`, params);
};

// 查询语义执行的数据
export const querySemanticData = function (params: {bk_biz_id: number, root_id: string}) {
  return http.post<QuerySemanticExecuteResultModel>(`/apis/mysql/bizs/${params.bk_biz_id}/sql_import/query_semantic_data/`, params)
    .then(data => ({
      ...data,
      semantic_data: new SemanticDataModel(data.semantic_data),
    }));
};

// 获取用户语义检查任务列表
export const getUserSemanticTasks = function (params: {
  bk_biz_id: number,
  cluster_type?: string
}) {
  return http.get<UserSemanticTaskModel[]>(`/apis/mysql/bizs/${params.bk_biz_id}/sql_import/get_user_semantic_tasks/`, params)
    .then(data => data.map(item => new UserSemanticTaskModel(item)));
};

// 删除语义检查任务
export const deleteUserSemanticTasks = function (params: {
  bk_biz_id: number,
  task_ids: string[],
  cluster_type: string,
}) {
  return http.delete<number>(`/apis/mysql/bizs/${params.bk_biz_id}/sql_import/delete_user_semantic_tasks/`, params);
};
