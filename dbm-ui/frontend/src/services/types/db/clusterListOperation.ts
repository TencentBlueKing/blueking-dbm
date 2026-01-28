import type { PipelineStatus } from '@common/const';

export interface ClusterListOperation {
  cluster_id: number;
  flow_id: number;
  status: PipelineStatus;
  ticket_id: number;
  ticket_type: string;
  title: string;
}
