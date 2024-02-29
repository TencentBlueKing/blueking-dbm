import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types';

const { currentBizId } = useGlobalBizs();

const path = '/apis/mysql/bizs';

// 开区模板列表
export const getList = function (params: {
  config_name?: string;
  bk_biz_id?: number;
  cluster_type?: 'tendbha' | 'tendbcluster';
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<OpenareaTemplateModel[]>>(`${path}/${currentBizId}/openarea/`, params).then((data) => ({
    ...data,
    results: data.results.map((item: OpenareaTemplateModel) => new OpenareaTemplateModel(item)),
  }));
};

// 新建开区
export const create = function (params: {
  bk_biz_id: number;
  config_name: string;
  config_rules: {
    data_tblist: string[];
    priv_data: number[];
    schema_tblist: string[];
    source_db: string;
    target_db_pattern: string;
  }[];
  source_cluster_id: number;
  cluster_type?: 'tendbha' | 'tendbcluster';
}) {
  return http.post(`${path}/${currentBizId}/openarea/`, params);
};

// 删除开区模板
export const remove = function (params: { id: number }) {
  return http.delete(`${path}/${currentBizId}/openarea/${params.id}/`);
};

// 获取开区结果预览
export const getPreview = function (params: {
  config_id: number;
  config_data: {
    cluster_id: number;
    vars: Record<string, any>;
    authorize_ips: string[];
  }[];
}) {
  return http.post<{
    config_data: {
      cluster_id: number;
      execute_objects: {
<<<<<<< HEAD
        authorize_ips: string[],
        data_tblist: string[],
        error_msg: string,
        priv_data: number[],
        schema_tblist: string[],
        source_db: string,
        target_db: string,
      }[],
      target_cluster_domain: string,
    }[],
=======
        authorize_ips: string[];
        data_tblist: string[];
        priv_data: number[];
        schema_tblist: string[];
        source_db: string;
        target_db: string;
      }[];
      target_cluster_domain: string;
    }[];
>>>>>>> c3acfbeaf (style(frontend): 使用prettier代码格式化 #3408)
    rules_set: {
      account_rules: {
        bk_biz_id: number;
        dbname: string;
      }[];
      bk_biz_id: number;
      cluster_type: string;
      operator: string;
      source_ips: string[];
      target_instances: string[];
      user: string;
    }[];
  }>(`${path}/${currentBizId}/openarea/preview/`, params);
};

// 开区模板详情
export const getDetail = function (params: { id: number }) {
  return http
    .get<OpenareaTemplateModel>(`${path}/${currentBizId}/openarea/${params.id}/`)
    .then((data) => new OpenareaTemplateModel(data));
};

// 更新开区模板
export const update = function (params: {
  id: number;
  bk_biz_id: number;
  config_name: string;
  config_rules: {
    data_tblist: string[];
    priv_data: number[];
    schema_tblist: string[];
    source_db: string;
    target_db_pattern: string;
  }[];
  source_cluster_id: number;
  cluster_type?: 'tendbha' | 'tendbcluster';
}) {
  const realParams = { ...params } as { id?: number };
  delete realParams.id;

  return http.put(`${path}/${currentBizId}/openarea/${params.id}/`, realParams);
};

export const updateVariable = function <T extends 'add' | 'update' | 'delete'>(params: {
  op_type: T;
  old_var: T extends 'update' | 'delete'
    ? {
        name: string;
        builtin: boolean;
        desc: string;
      }
    : undefined;
  new_var: T extends 'add' | 'update'
    ? {
        name: string;
        builtin: boolean;
        desc: string;
      }
    : undefined;
}) {
  return http.post(`${path}/${currentBizId}/openarea/alter_var/`, params);
};
