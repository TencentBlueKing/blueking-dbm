export interface ClusterCommonInfo {
  availableTags: ClusterCommonInfo['tags'];
  create_at: string;
  db_type: string;
  id: number;
  masterDomain: string;
  phase: string;
  tags: {
    id: number;
    is_builtin: boolean;
    key: string;
    system: boolean;
    value: string;
  }[];
  update_at: string;
}
