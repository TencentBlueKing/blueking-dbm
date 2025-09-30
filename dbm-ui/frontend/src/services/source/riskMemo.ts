import RiskMemoDetailModel from '@services/model/risk-memo/risk-memo-detail';
import type { ListBase } from '@services/types';

import http from '../http';

const path = '/apis/risk_memo';

// 业务风险/业务特殊要求列表
export const getRiskMemoList = (params: {
  bk_biz_id?: number;
  is_assist?: boolean;
  is_special: boolean;
  limit?: number;
  offset?: number;
  platform?: boolean;
}) => {
  return http.get<
    ListBase<
      {
        biz_inpact: string[];
        bk_biz_id: number;
        db_type: string;
        description: string;
        duration_time: number;
        id: number;
        inpact_cluster: string[];
        is_special: boolean;
        level: string;
        name: string;
        status: string;
      }[]
    >
  >(`${path}/`, params);
};

// 业务风险/业务特殊要求详情
export const getRiskMemoDetail = (params: { risk_id: number }) => {
  return http.get<RiskMemoDetailModel>(`${path}/${params.risk_id}/`, params);
};

// 创建业务风险/具体特殊要求
export const createRiskMemo = (params: {
  biz_inpact?: string;
  bk_biz_id: number;
  db_type: string;
  description: string;
  inpact_cluster: string;
  is_special: boolean;
  level: string; // 固定 Middle
  name: string;
  status: 'backlog' | 'done';
}) => {
  return http.post<null>(`${path}/`, params);
};

// 更新业务风险/具体特殊要求
export const updateRiskMemo = (params: {
  biz_inpact?: string;
  bk_biz_id?: number;
  db_type?: string;
  description?: string;
  id: number;
  inpact_cluster?: string;
  is_special?: boolean;
  level?: string;
  name?: string;
  status?: string;
}) => {
  return http.put<null>(`${path}/${params.id}/`, params);
};

// 更新业务风险/具体特殊要求状态
export const updateRiskStatus = (params: {
  final_content?: string; // 结项内容  非必传  结项时候需要
  risk_id: number;
  status: 'backlog' | 'done';
}) => {
  return http.post<null>(`${path}/${params.risk_id}/update_risk_status/`, params);
};

// 获取业务风险/具体特殊要求操作记录
export const getRiskOperateRecords = (params: { limit?: number; offset?: number; risk: number }) => {
  return http.get<
    ListBase<
      {
        create_at: string;
        creator: string;
        id: number;
        oper_type: string;
        oper_type_value: string;
        risk: number;
        update_at: string;
        updater: string;
      }[]
    >
  >(`${path}/get_risk_operate_records/`, params);
};

// 创建跟进
export const createRiskFollowUp = (params: {
  content: string; // 跟进内容
  risk: number;
}) => {
  return http.post<null>(`${path}/follow_up/`, params);
};

// 更新跟进
export const updateRiskFollowUp = (params: {
  content: string; // 跟进内容
  id: number;
  risk: number;
}) => {
  return http.put<null>(`${path}/follow_up/${params.id}/`, params);
};

// 删除跟进
export const deleteRiskFollowUp = (params: { id: number }) => {
  return http.delete<null>(`${path}/follow_up/${params.id}/`);
};

// 获取业务影响类型
export const getBizInpactList = () => {
  return http.get<
    {
      label: string;
      value: string;
    }[]
  >(`${path}/get_biz_inpact_list/`);
};
