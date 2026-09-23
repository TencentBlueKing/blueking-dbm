export interface ClusterCommonInfo {
  availableTags: ClusterCommonInfo['tags'];
  bk_biz_id?: number;
  create_at: string;
  db_type: string;
  id: number;
  is_public?: boolean;
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
