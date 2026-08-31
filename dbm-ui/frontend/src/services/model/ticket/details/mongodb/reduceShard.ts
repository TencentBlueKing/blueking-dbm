import type { DetailBase, DetailClusters } from '../common';

export interface ReduceShard extends DetailBase {
  bk_cloud_id?: number; // 非必传
  clusters: DetailClusters;
  infos: {
    cluster_id: number;
    // 该集群当前分片数（详情展示用，最终分片数前端演算）
    current_shard_num?: number;
    // 缩容方式：指定分片 / 指定数量
    reduce_mode: 'by_shard_names' | 'by_count';
    // 指定数量模式：缩容分片数
    reduce_shards_num?: number;
    // 指定分片模式：待删分片名列表
    shard_names?: string[];
  }[];
}
