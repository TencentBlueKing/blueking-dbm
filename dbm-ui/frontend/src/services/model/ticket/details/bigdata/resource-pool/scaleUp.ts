import type { ResourcePoolDetailBase } from '../../common';

import type { ExtInfo, Nodes, ResourceSpec } from './common';

export interface ScaleUp extends ResourcePoolDetailBase {
  cluster_id: number;
  ext_info: ExtInfo;
  nodes: Nodes;
  resource_spec: ResourceSpec;
}
