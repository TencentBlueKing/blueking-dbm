import SpiderModel from '@services/model/spider/spider';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types/common';

export const getList = function (params: Record<string, any>) {
  const { currentBizId } = useGlobalBizs();

  return http.get<ListBase<SpiderModel[]>>(`/apis/mysql/bizs/${currentBizId}/spider_resources/`, params)
    .then(data => ({
      ...data,
      results: data.results.map((item: SpiderModel) => new SpiderModel(item)),
    }));
};
