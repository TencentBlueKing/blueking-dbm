import http from '@services/http/index';
import ResourceTag from '@services/model/db-resource/ResourceTag';
import type { ListBase } from '@services/types/listBase';

const path = '/apis/tag/';

/**
 * 查询资源标签
 */
export function listTag(params: {
  value?: string;
  bind_ips?: string[];
  creator?: string;
  bk_biz_id: number;
  limit?: number;
  offset?: number;
}) {
  return http.get<ListBase<ResourceTag[]>>(`${path}list_resource_tags/`, params).then((res) => ({
    ...res,
    results: res.results.map((item: ResourceTag) => new ResourceTag(item)),
  }));
}

/**
 * 新增资源标签
 */
export function createTag(params: {
  bk_biz_id: number;
  type: string; // 固定为 system
  key: string; // 固定为 resource
  value: string[];
}) {
  return http.post(`${path}`, params);
}

/**
 * 批量删除资源标签
 */
export function deleteTag(params: { ids: number[] }) {
  return http.delete(`${path}batch_delete/`, params);
}

/**
 * 编辑资源标签
 */
export function updateTag(params: { id: number; value: string }) {
  return http.patch(`${path}`, params);
}

/**
 * 校验标签名是否重复
 */
export function validateTag(params: { bk_biz_id: number; values: string[] }) {
  return http.post<{ duplicated_values: string[] }>(`${path}verify_duplicated_name/`, params);
}
