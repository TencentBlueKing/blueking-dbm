import ResourceTagModel from '@services/model/db-resource/ResourceTag';
import type { ListBase } from '@services/types/listBase';

import http from '../http';

const path = '/apis/tag';

/**
 * 查询资源标签
 */
export function listTag(params: {
  bind_ips?: string[];
  bk_biz_id?: number;
  bk_biz_ids?: string; // 业务ID列表，逗号分隔
  creator?: string;
  ids?: string;
  limit?: number;
  offset?: number;
  ordering?: string;
  type: 'resource' | 'cluster';
  value?: string;
}) {
  return http.get<ListBase<ResourceTagModel[]>>(`${path}/`, params).then((res) => ({
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
  type: 'resource' | 'cluster';
}) {
  return http.post<
    {
      id: number;
    }[]
  >(`${path}/batch_create/`, params);
}

/**
 * 批量删除资源标签
 */
export function deleteTag(params: { bk_biz_id: number; ids: number[] }) {
  return http.delete(`${path}/batch_delete/`, params);
}

/**
 * 编辑资源标签
 */
export function updateTag(params: { bk_biz_id: number; id: number; type: string; value: string }) {
  return http.patch(`${path}/${params.id}/`, params);
}

/**
 * 校验标签是否重复，并返回重复的标签值
 */
export function validateTag(params: {
  bk_biz_id: number;
  is_builtin?: boolean;
  tags: {
    key: string;
    value: string;
  }[];
  type: 'resource' | 'cluster';
}) {
  return http.post<{ key: string; value: string }[]>(`${path}/verify_duplicated/`, params);
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
  >(`${path}/related_resources/`, params);
}

/**
 * 批量创建标签
 */
export function batchCreateTags(params: {
  bk_biz_id: number;
  tags: {
    key: string;
    value: string;
  }[];
  type: string;
}) {
  return http.post(`${path}/batch_create/`, params);
}

/**
 * 查询标签关联资源
 */
export function listTagRelatedResource(params: { ids: number[]; resource_type: string }) {
  return http.post<
    {
      id: number;
      related_resources: {
        display: string;
        id: number;
      }[];
    }[]
  >(`${path}/related_resources/`, params);
}

/**
 * 查询集群标签
 */
export function listClusterTag(params: {
  bind_ips?: string[];
  bk_biz_id?: number;
  creator?: string;
  ids?: string;
  limit?: number;
  offset?: number;
  ordering?: string;
  type?: string;
  value?: string;
}) {
  return http
    .get<
      ListBase<
        Array<
          {
            clusters: {
              domain: string;
              id: number;
            };
          } & ResourceTagModel
        >
      >
    >(`${path}/`, params)
    .then(async (data) => {
      const ids = data.results.map((item) => item.id);
      const relatedResource = await listTagRelatedResource({
        ids,
        resource_type: 'cluster',
      });
      const relatedResourceMap = relatedResource.reduce<
        Record<
          number,
          {
            domain: string;
            id: number;
          }[]
        >
      >((results, item) => {
        Object.assign(results, {
          [item.id]: item.related_resources.map((item) => ({
            domain: item.display,
            id: item.id,
          })),
        });
        return results;
      }, {});
      return {
        count: data.count,
        results: data.results.map((item) =>
          Object.assign(new ResourceTagModel(item), {
            clusters: relatedResourceMap[item.id] || [],
            permission: data.permission,
          }),
        ),
      };
    });
}
