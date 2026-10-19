import type { DetailBase, DetailClusters, DetailSpecs } from '../common';

export interface Rollback extends DetailBase {
  clusters: DetailClusters;
  infos: {
    // 是否允许 binlog 序号不连续（仅 TendisSSD / TendisPlus 生效）
    allow_binlog_nonconsecutive: boolean;
    // 备份批次标识，如 SCHEDULED-2026100803
    backup_identify: string;
    cluster_id: number;
    // 构造到的时间点，空串表示仅用全备（字段名待后端确认，见 openspec design Open Questions）
    recovery_time_point: string;
    resource_spec: {
      redis: {
        count: number;
        label_names: string[];
        labels: string[];
        spec_id: number;
      };
    };
    // 勾选的分片列表，空数组表示该批次全部分片
    shard_values: string[];
  }[];
  ip_source: 'resource_pool';
  specs: DetailSpecs;
}
