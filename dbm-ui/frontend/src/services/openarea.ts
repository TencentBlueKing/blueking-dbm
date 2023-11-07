import OpenareaModel from '@services/model/openarea/openarea';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types/common';

const { currentBizId } = useGlobalBizs();

// 开区模板列表
export const getList = function (params: Record<string, any>) {
  return http.get<ListBase<OpenareaModel[]>>(`/apis/mysql/bizs/${currentBizId}/openarea/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: OpenareaModel) => new OpenareaModel(item)),
    }));
};

// 删除开区模板
export const remove = function (params: { id: number }) {
  return http.delete(`/apis/mysql/bizs/${currentBizId}/openarea/${params.id}`);
};
