export interface ClusterListNode {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  bk_sub_zone: string;
  instance: string;
  /** MongoDB：元数据角色 m1/m2/…/backup */
  instance_role?: string;
  ip: string;
  /** MongoDB：巡检运行时状态 PRIMARY/SECONDARY/… */
  mongodb_state?: string | null;
  name: string;
  phase: string;
  port: number;
  /** MongoDB 分片：ShardSvr 分片名 */
  seg_range?: string;
  spec_config: {
    count: number;
    cpu: {
      max: number;
      min: number;
    };
    device_class: string[];
    id: number;
    mem: {
      max: number;
      min: number;
    };
    name: string;
    qps: {
      max: number;
      min: number;
    };
    storage_spec: {
      max: number;
      min: number;
      mount_point: string;
      size?: number;
      type: string;
    }[];
  };
  status: 'running' | 'unavailable';
  version: '';
}
