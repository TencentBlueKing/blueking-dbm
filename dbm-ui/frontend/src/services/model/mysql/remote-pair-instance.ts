export default class RemotePaisInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id: number;
  instance: string;
  ip: string;
  name: string;
  port: number;
  phase: string;
  spec_config: {
    id: number;
  };
  status: string;

  constructor(payload = {} as RemotePaisInstance) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.bk_instance_id = payload.bk_instance_id;
    this.instance = payload.instance;
    this.ip = payload.ip;
    this.name = payload.name;
    this.port = payload.port;
    this.phase = payload.phase;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
  }
}
