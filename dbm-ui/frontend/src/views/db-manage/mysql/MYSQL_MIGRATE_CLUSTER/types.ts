/**
 * CLUSTER_MIGRATE: 集群迁移
 * HOST_MIGRATE: 整机迁移
 */
export enum MigrateTypes {
  CLUSTER_MIGRATE = 'CLUSTER_MIGRATE',
  HOST_MIGRATE = 'HOST_MIGRATE',
}

export interface TicketInfo {
  cluster_ids: number[];
  resource_spec: {
    new_master: {
      spec_id: 0;
      hosts: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    new_slave: TicketInfo['resource_spec']['new_master'];
  };
  display_info: {
    type: MigrateTypes;
  };
}
