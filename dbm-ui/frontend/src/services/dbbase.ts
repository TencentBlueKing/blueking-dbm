import http from './http';

// 查询集群名字是否重复
export  function verifyDuplicatedClusterName(params: {
  cluster_type: string,
  name: string,
  bk_biz_id: number
}) {
  return http.get<boolean>('/apis/dbbase/verify_duplicated_cluster_name/', params);
}
