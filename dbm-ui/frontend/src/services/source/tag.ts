import ResourceTagModel from '@services/model/db-resource/ResourceTag';
import type { ListBase } from '@services/types/listBase';

import http from '../http';

const path = '/apis/tag/';

/**
 * 查询资源标签
 */
export function listTag(params: {
  value?: string;
  bind_ips?: string[];
  creator?: string;
  bk_biz_id?: number;
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<ResourceTagModel[]>>(`${path}`, params).then((res) => ({
    ...res,
    results: res.results.map((item: ResourceTagModel) => new ResourceTagModel(item)),
  }));
}

/**
 * 新增资源标签
 */
export function createTag(params: {
  bk_biz_id: number;
  tags: {
    key: string; // 固定为 dbresource
    value: string;
  }[];
}) {
  return http.post(`${path}batch_create/`, params);
}

/**
 * 批量删除资源标签
 */
export function deleteTag(params: { bk_biz_id: number; ids: number[] }) {
  return http.delete(`${path}batch_delete/`, params);
}

/**
 * 编辑资源标签
 */
export function updateTag(params: { bk_biz_id: number; id: number; value: string }) {
  return http.patch(`${path}${params.id}/`, params);
}

/**
 * 校验标签是否重复，并返回重复的标签值
 */
export function validateTag(params: {
  bk_biz_id: number;
  tags: {
    key: string;
    value: string;
  }[];
}) {
  return http.post<{ key: string; value: string }[]>(`${path}verify_duplicated/`, params);
}

/**
 * 根据标签id获取关联IP
 */
export function getTagRelatedResource(params: { bk_biz_id: number; ids: number[]; resource_type?: string }) {
  return http.post<
    {
      id: number;
      ip_count: number;
    }[]
  >(`${path}related_resources/`, params);
}
