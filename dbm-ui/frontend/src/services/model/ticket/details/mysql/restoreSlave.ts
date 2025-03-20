import type { DetailBase, DetailClusters } from '../common';

/**
 * MySQL Slave重建
 */
export interface RestoreSlave extends DetailBase {
  backup_source: string;
  clusters: DetailClusters;
  infos: {
    cluster_ids: number[];
    new_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    old_slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }[];
}

// export interface RestoreSlave extends DetailBase {
//   backup_source: string;
//   clusters: DetailClusters;
//   ip_source: 'resource_pool';
//   infos: {
//     cluster_ids: number[];
//     resource_spec: {
//       new_slave: {
//         hosts: {
//           bk_biz_id: number;
//           bk_cloud_id: number;
//           bk_host_id: number;
//           ip: string;
//           port?: number;
//         }[];
//         spec_id: number;
//       };
//     };
//     old_nodes: {
//       old_slave: {
//         bk_biz_id: number;
//         bk_cloud_id: number;
//         bk_host_id: number;
//         ip: string;
//         port?: number;
//       }[];
//     };
//   }[];
// }
