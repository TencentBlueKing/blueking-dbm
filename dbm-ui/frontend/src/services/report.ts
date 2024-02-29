import http, { type IRequestPayload } from './http';
import type { ListBase } from './types/common';

interface IResult {
  results: Record<string, unknown>[];
  name: string;
  title: {
    name: string;
    display_name: string;
    format: 'text' | 'status' | 'fail_slave_instance';
  }[];
}

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
  >('/db_report/checksum_check/instance', params, payload);
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
export const getDbmonHeartbeat = function (params: Record<string, any>) {
  return http.get<IResult>('/db_report/dbmon/heartbeat', params);
};

// redis binlog检查报告
export const getRedisCheckBinlogBackup = function (params: Record<string, any>) {
  return http.get<IResult>('/db_report/redis_check/binlog_backup', params);
};

// redis 全备检查报告
export const getRedisCheckFullBackup = function (params: Record<string, any>) {
  return http.get<IResult>('/db_report/redis_check/full_backup', params);
};

// redis 孤立节点检查报告
export const getRedisMetaCheckAloneInstance = function (params: Record<string, any>) {
  return http.get<IResult>('/db_report/redis_meta_check/alone_instance', params);
};

// 实例状态异常检查
export const getRedisMetaCheckStatusAbnormal = function (params: Record<string, any>) {
  return http.get<IResult>('/db_report/redis_meta_check/status_abnormal', params);
};
