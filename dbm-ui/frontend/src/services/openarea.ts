import OpenareaModel from '@services/model/openarea/openarea';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types/common';

const { currentBizId } = useGlobalBizs();

export const getList = function (params = {}) {
  return http.get<ListBase<OpenareaModel[]>>(`/apis/mysql/bizs/${currentBizId}/openarea/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: OpenareaModel) => new OpenareaModel(item)),
    }));
};
