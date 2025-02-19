import type { ResourcePoolDetailBase } from '../../common';

import type { Nodes, ResourceSpec } from './common';

export interface Replace extends ResourcePoolDetailBase {
  cluster_id: number;
  old_nodes: Nodes;
  resource_spec: ResourceSpec;
}
