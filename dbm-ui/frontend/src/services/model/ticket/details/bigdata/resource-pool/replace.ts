import type { ResourcePoolDetailBase } from '../../common';

import type { Nodes, ResourceSpec } from './common';

/**
 * 大数据集群-替换
 */
export interface Replace extends ResourcePoolDetailBase {
  cluster_id: number;
  old_nodes: Nodes;
  resource_spec: ResourceSpec;
}
