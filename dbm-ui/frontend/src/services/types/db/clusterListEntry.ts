export interface ClusterListEntry {
  cluster_entry_type: string;
  entry: string;
  instance_role: string;
  // 入口端口由后端返回（VictoriaMetrics 等按 role 区分多入口场景）
  port?: number;
  role: string;
}
