export default class DeployPlan {
  capacity: number;
  cluster_type: string;
  create_at: string;
  creator: string;
  desc: string;
  id: number;
  is_refer: boolean;
  machine_pair_cnt: number;
  name: string;
  shard_cnt: number;
  spec: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as DeployPlan) {
    this.capacity = payload.capacity;
    this.cluster_type = payload.cluster_type;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.desc = payload.desc;
    this.id = payload.id;
    this.is_refer = Boolean(payload.is_refer);
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.name = payload.name;
    this.shard_cnt = payload.shard_cnt;
    this.spec = payload.spec;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
  }
}
