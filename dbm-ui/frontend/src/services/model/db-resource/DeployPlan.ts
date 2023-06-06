export default class DeployPlan {
  id: number;
  capacity: number;
  cluster_type: string;
  creator: string;
  create_at: string;
  desc: string;
  machine_pair_cnt: number;
  name: string;
  shard_cnt: number;
  spec: number;
  updater: string;
  update_at: string;

  constructor(payload = {} as DeployPlan) {
    this.id = payload.id;
    this.capacity = payload.capacity;
    this.cluster_type = payload.cluster_type;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.desc = payload.desc;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.name = payload.name;
    this.shard_cnt = payload.shard_cnt;
    this.spec = payload.spec;
    this.updater = payload.updater;
    this.update_at = payload.update_at;
  }
}
