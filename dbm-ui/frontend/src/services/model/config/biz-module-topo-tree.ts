type NodeType = 'biz' | 'module';

export default class BizModuleTopoTree {
  id: number;
  name?: string;
  nodeType?: NodeType;
  count?: number;
  children?: Array<BizModuleTopoTree>;

  constructor(payload = {} as BizModuleTopoTree) {
    this.id = payload.id;
    this.name = payload.name;
    this.nodeType = payload.nodeType;
    this.count = payload.count;
    this.children = payload.children;
  }
}
