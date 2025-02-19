import type { ResourcePoolDetailBase } from '../../common';

import type { ExtInfo, Nodes, ResourceSpec } from './common';

export interface Shrink extends ResourcePoolDetailBase {
  cluster_id: number;
  ext_info: ExtInfo;
  old_nodes: Nodes;
  resource_spec: ResourceSpec;
}
