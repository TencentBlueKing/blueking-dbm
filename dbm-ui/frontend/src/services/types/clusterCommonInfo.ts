export interface ClusterCommonInfo {
  create_at: string;
  db_type: string;
  id: number;
  masterDomain: string;
  phase: string;
  sortedTags: ClusterCommonInfo['tags'];
  tags: {
    id: number;
    is_builtin: boolean;
    key: string;
    value: string;
  }[];
  update_at: string;
}
