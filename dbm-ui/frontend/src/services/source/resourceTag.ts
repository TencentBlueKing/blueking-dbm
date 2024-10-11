import http from '../http';
import ResourceTagModel from '../model/db-resource/ResourceTag';
import type { ListBase } from '../types/listBase';

const path = '/api/mock';

/**
 * 查询资源标签
 */
export function getResourceTags() {
  return http.post<ListBase<ResourceTagModel[]>>(`${path}/query_tags/`).then((res) => ({
    ...res,
    results: res.results.map((item: ResourceTagModel) => new ResourceTagModel(item)),
  }));
}

/**
 * 批量删除资源标签
 */
export function deleteResourceTags(params: { ids: number[] }) {
  return http.post(`${path}/delete_tags/`, params);
}

/**
 * 新增资源标签
 */
export function createResourceTag(params: { tags: string[] }) {
  return http.post(`${path}/add_tag/`, params);
}

/**
 * 修改资源标签
 */
export async function modifyResourceTag(params: { data: ResourceTagModel }) {
  return http.post(`${path}/mod_tag/`, params);
}

/**
 * 获取所有的资源标签
 */
export async function getAllResourceTags() {
  return http.post<{ results: string[] }>(`${path}/query_all_tags/`);
}
