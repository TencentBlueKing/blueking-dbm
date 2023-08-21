import PartitionModel from '@services/model/partition/partition';
import PartitionLogModel from '@services/model/partition/partition-log';

import { useGlobalBizs } from '@stores';

import http from './http';
import type { ListBase } from './types/common';

// 分区列表
export const getList = function (params: Record<string, any>) {
  return http.get<ListBase<PartitionModel[]>>('/apis/partition/', params)
    .then(data => ({
      ...data,
      results: data.results.map((item: PartitionModel) => new PartitionModel(item)),
    }));
};

// 增加分区策略
export const create = function (params: {
  cluster_id: number,
  dblikes: string[],
  tblikes: string[],
  partition_column: string,
  partition_column_type: string,
  expire_time: number,
  partition_time_interval: number,
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post('/apis/partition/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 批量删除
export const batchRemove = function (params: {
  cluster_type: string,
  ids: number[],
}) {
  const { currentBizId } = useGlobalBizs();
  return http.delete('/apis/partition/batch_delete/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 禁用
export const disablePartition = function (params: {
  cluster_type: string,
  ids: number[],
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post('/apis/partition/disable/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 启用
export const enablePartition = function (params: {
  cluster_type: string,
  ids: number[],
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post('/apis/partition/enable/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 分区策略前置执行
export const dryRun = function (params: {
  config_id: number,
  cluster_id: number,
  cluster_type: string,
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post<Record<number, {
    execute_objects: {
      add_partition: string[],
      config_id: number,
      dblike: string,
      drop_partition: string[],
      init_partition: {
        need_size: number,
        sql: string
      }[],
      tblike: string
    }[],
    ip: string,
    message: string,
    port: number,
    shard_name: string
  }[]>>('/apis/partition/dry_run/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 分区策略执行
export const execute = function (params: {
  cluster_id: number,
  partition_objects: Record<any, unknown>,
}) {
  return http.post<{
    id: number
  }>('/apis/partition/execute_partition/', params);
};

// 查询分区策略日志
export const queryLog = function (params: {
  cluster_type: string,
  config_id: number,
}) {
  return http.get<ListBase<PartitionLogModel[]>>('/apis/partition/query_log/', params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new PartitionLogModel(item)),
    }));
};

// 分区策略字段校验
export const verifyPartitionField = function (params: {
  cluster_id: number,
  dblikes: string[],
  tblikes: string[],
  partition_column: string,
  partition_column_type: string,
}) {
  return http.post('/apis/partition/verify_partition_field/', params);
};

// 修改分区策略
export const edit = function (params: {
  id: number,
  cluster_id: number,
  dblikes: string[],
  tblikes: string[],
  partition_column: string,
  partition_column_type: string,
  expire_time: number,
  partition_time_interval: number,
}) {
  const realParams = { ...params } as { id?: number, };
  delete realParams.id;

  return http.put(`/apis/partition/${params.id}/`, {
    ...realParams,
  });
};
