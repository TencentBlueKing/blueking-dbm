import type { ListBase } from '@services/types';

import http, { type IRequestPayload } from '../http';

interface IResult {
  count: number;
  results: Record<string, unknown>[];
  name: string;
  title: {
    name: string;
    display_name: string;
    format: 'text' | 'status' | 'fail_slave_instance';
  }[];
}

const path = '/db_report';

// 数据校验
export const getChecksumReport = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/checksum_check/report', params, payload);
};

// 失败的从库实例详情
export const getChecksumInstance = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<
    ListBase<
      {
        details: Record<string, string[]>;
        id: number;
        ip: string;
        master_ip: string;
        master_port: string;
        port: string;
      }[]
    >
  >('/db_report/checksum_instance/', params, payload);
};

// 元数据检查报告列表
export const getMetaCheckInsganceBelong = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/meta_check/instance_belong', params, payload);
};

// binlog检查报告
export const getmysqlCheckBinlogBackup = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/mysql_check/binlog_backup', params, payload);
};

// 全备检查报告
export const getmysqlCheckFullBackup = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/mysql_check/full_backup', params, payload);
};

// dbmon心跳超时检查报告
export const getDbmonHeartbeat = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/dbmon/heartbeat', params, payload);
};

// redis binlog检查报告
export const getRedisCheckBinlogBackup = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/redis_check/binlog_backup', params, payload);
};

// redis 全备检查报告
export const getRedisCheckFullBackup = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/redis_check/full_backup', params, payload);
};

// redis 孤立节点检查报告
export const getRedisMetaCheckAloneInstance = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/redis_meta_check/alone_instance', params, payload);
};

// 实例状态异常检查
export const getRedisMetaCheckStatusAbnormal = function (params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<IResult>('/db_report/redis_meta_check/status_abnormal', params, payload);
};

// 巡检通用接口视图
export function getReportOverview() {
  return http.get<Record<string, string[]>>(`${path}/get_report_overview/`);
}

// 巡检总览统计接口
export function getReportCount() {
  return http.get<
    Record<
      string,
      Record<
        string,
        {
          assist_count: number;
          manage_count: number;
        }
      >
    >
  >(
    `${path}/get_report_count/`,
    {},
    {
      cache: 2000,
    },
  );
}

// 巡检报告通用接口
export function getReport(path: string, params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.get<{
    count: number;
    name: string;
    results: Record<string, string>[];
    title: {
      name: string;
      display_name: string;
      format: string;
    }[];
  }>(path, params, payload);
}
