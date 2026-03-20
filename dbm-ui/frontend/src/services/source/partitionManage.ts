import PartitionModel from '@services/model/partition/partition';
import type { ListBase } from '@services/types';

import { useGlobalBizs } from '@stores';

import type { ClusterTypes } from '@common/const';

import http from '../http';

// 分区列表
export const getList = function (params: Record<string, any>) {
  return http.get<ListBase<PartitionModel[]>>('/apis/partition/', params).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new PartitionModel(
          Object.assign(item, {
            permission: Object.assign({}, data.permission, item.permission),
          }),
        ),
    ),
  }));
};

// 增加分区策略，会创建单据且只有一个
export const create = function (params: {
  cluster_id: number;
  dblikes: string[];
  expire_time: number;
  partition_column: string;
  partition_column_type: string;
  partition_time_interval: number;
  tblikes: string[];
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post<
    {
      id: number; // 单据id
    }[]
  >('/apis/partition/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 批量删除
export const batchRemove = function (params: { cluster_type: string; ids: number[] }) {
  const { currentBizId } = useGlobalBizs();
  return http.delete('/apis/partition/batch_delete/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 禁用
export const disablePartition = function (params: { cluster_type: string; ids: number[] }) {
  const { currentBizId } = useGlobalBizs();
  return http.post('/apis/partition/disable/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

// 启用
export const enablePartition = function (params: { cluster_type: string; ids: number[] }) {
  const { currentBizId } = useGlobalBizs();
  return http.post('/apis/partition/enable/', {
    bk_biz_id: currentBizId,
    ...params,
  });
};

interface IDryRunData {
  execute_objects: {
    add_partition: string[];
    config_id: number;
    dblike: string;
    drop_partition: string[];
    init_partition: {
      need_size: number;
      sql: string;
    }[];
    tblike: string;
  }[];
  ip: string;
  message: string;
  port: number;
  shard_name: string;
}

// 分区策略执行
export const execute = function (params: {
  bk_biz_id: number;
  partition_infos: {
    cluster_id: number;
    configs: {
      config_id: number;
      dblike: string;
      expire_time: number;
      extra_partition: number;
      partition_column: string;
      partition_column_type: string;
      partition_time_interval: number;
      partition_type: number;
      phase: string;
      tblike: string;
      time_zone: string;
    }[];
    force: boolean;
  }[];
}) {
  return http.post<
    {
      id: number;
    }[]
  >('/apis/partition/execute_partition_v2/', params);
};

// 分区策略字段校验
export const verifyPartitionField = function (params: {
  bk_biz_id: number;
  cluster_id: number;
  dblikes: string[];
  partition_column: string;
  partition_column_type: string;
  tblikes: string[];
}) {
  return http.post<string | null>('/apis/partition/verify_partition_field/', params);
};

// 分区v2查询分区字段类型
export const queryFieldType = function (params: {
  bk_biz_id: number;
  cluster_id: number;
  dblikes: string[];
  partition_column: string;
  tblikes: string[];
}) {
  return http.post<string | null>('/apis/partition/query_field_type_v2/', params);
};

// 修改分区策略
export const edit = function (params: {
  cluster_id: number;
  dblikes: string[];
  expire_time: number;
  id: number;
  partition_column: string;
  partition_column_type: string;
  partition_time_interval: number;
  tblikes: string[];
}) {
  const realParams = { ...params } as { id?: number };
  delete realParams.id;

  return http.put<Record<number, IDryRunData[]>>(`/apis/partition/${params.id}/`, {
    ...realParams,
  });
};

// 查询分区执行失败日志详情
export const saveAndExecute = function (params: {
  cluster_id: number;
  dblikes: string[];
  expire_time: number;
  force?: boolean;
  partition_column: string;
  partition_column_type: string;
  partition_time_interval: number;
  tblikes: string[];
}) {
  return http.post<
    {
      id: number;
    }[]
  >('/apis/partition/save_and_execute_v2/', params);
};

// 查询分区执行失败日志详情
export const queryLog = function (params: { config_id: number }) {
  return http.post<{
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_type: string;
    config_id: number;
    create_time: string;
    created_at: string;
    event_bk_biz_id: number;
    event_bk_cloud_id: number;
    event_create_timestamp: number;
    event_receive_timestamp: number;
    event_report_timestamp: number;
    event_source_ip: string;
    event_uuid: string;
    exec_log: string;
    id: number;
    status: string;
    updated_at: string;
  }>('/apis/partition/query_log_v2/', params);
};

// Excel导入分区策略
export const importFromExcel = function (params: { file: File }) {
  return http.post<{
    failed_count: number;
    failed_items: {
      additionalProp1: string;
      additionalProp2: string;
      additionalProp3: string;
    }[];
    success_count: number;
  }>('/apis/partition/import_from_excel/', params);
};

// 导出分区策略
export const exportPartitions = function (params: {
  bk_biz_id: number;
  cluster_type: ClusterTypes;
  export_type: string; // all-所有分区策略，selected-选中分区策略
  selected_ids?: number[];
}) {
  return http.post<{
    file_content: string;
    file_name: string;
    total_count: number;
  }>('/apis/partition/export_partitions/', params, { responseType: 'blob' });
};
