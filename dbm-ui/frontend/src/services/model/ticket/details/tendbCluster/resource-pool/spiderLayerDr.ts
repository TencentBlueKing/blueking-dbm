import type { ResourcePoolDetailBase } from '../../resource-pool';

/**
 * TenDBCluster 接入层故障重建（故障修复类）
 * 集群所选接入层角色（Spider Master / Spider Slave）整组不可用、无法在原机器上立即恢复时，
 * 按集群整组申请新机重建并下架旧机
 */

interface ResourceSpecItem {
  count: number;
  label_names: string[]; // 标签名称列表，单据详情回显用
  labels: string[]; // 标签id列表
  spec_id: number;
}

export interface SpiderLayerDr extends ResourcePoolDetailBase {
  infos: {
    cluster_id: number;
    old_nodes: {
      proxy: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    resource_spec: {
      spider_master_new_ip_list?: ResourceSpecItem;
      spider_slave_new_ip_list?: ResourceSpecItem;
    };
    strip_dns_before_install: boolean;
  }[];
}
