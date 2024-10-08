import http from '../http';
import ResourceTagModel, { type IResourceTag } from '../model/db-resource/ResourceTag';
import type { ListBase } from '../types/listBase';

const path = '/api/mock';

/**
 * 查询资源标签
 */
export function getResourceTags() {
  return http.post<ListBase<ResourceTagModel[]>>(`${path}/query_tags/`).then((res) => ({
    ...res,
    results: res.results.map((item: IResourceTag) => new ResourceTagModel(item)),
  }));
}

/**
 * 批量删除资源标签
 */
export async function deleteResourceTags(ids: number[]) {
  return http.post(`${path}/delete_tags/`, { ids });
}

/**
 * 新增资源标签
 */
export async function createResourceTag(tags: string[]) {
  return http.post(`${path}/add_tag/`, { tags });
}

/**
 * 修改资源标签
 */
export async function modifyResourceTag(data: ResourceTagModel) {
  return http.post(`${path}/mod_tag/`, { data });
}

/**
 * 获取所有的资源标签
 */
export async function getAllResourceTags() {
  return http.post<{ results: string[] }>(`${path}/query_all_tags/`);
}
