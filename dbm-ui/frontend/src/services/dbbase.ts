import http from './http';

// 查询集群名字是否重复
export function verifyDuplicatedClusterName(params: { cluster_type: string; name: string; bk_biz_id: number }) {
  return http.get<boolean>('/apis/dbbase/verify_duplicated_cluster_name/', params);
}

// 查询全集群信息
export function queryAllTypeCluster(params: {
  bk_biz_id: number;
  cluster_types?: string;
  immute_domain?: string;
  phase?: string;
}) {
  return http.get<
    {
      bk_cloud_id: number;
      cluster_type: string;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      region: string;
    }[]
  >('/apis/dbbase/simple_query_cluster/', params);
}
