export default class BizModuleTopoTree {
  bk_biz_name: string;
  bk_biz_id: number;
  count: number;
  modules: {
    module_name: string;
    module_id: number;
    count: number;
  }[];

  constructor(payload = {} as BizModuleTopoTree) {
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_biz_id = payload.bk_biz_id;
    this.count = payload.count;
    this.modules = payload.modules || [];
  }
}
