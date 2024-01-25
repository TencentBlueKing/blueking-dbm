import dayjs from 'dayjs';

import { t } from '@locales';

<<<<<<< HEAD
export default class SqlServerCluster {
=======
export default class SQLServerClusterList {
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  static statusMap: Record<string, string> = {
    running: t('正常'),
    unavailable: t('异常'),
  };
  static themes: Record<string, string> = {
    running: 'success',
  };

  belong_DB_module: string;
  bk_cloud_name: string;
  bk_host_id: number;
  clusterId: number;
  cluster_name: string;
  cluster_type: string;
  control_area: string;
  create_time: string;
  create_user: string;
  id: number;
  instance_name: string;
  master_enter: string;
  operation: string;
  proxies: Array<{
    bk_instance_id: number,
    ip: string,
    name: string,
    port: number,
    status: string
  }>;
  slave_enter: string;
  status: string;

<<<<<<< HEAD
  constructor(payload: SqlServerCluster) {
=======
  constructor(payload: SQLServerClusterList) {
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
    this.belong_DB_module = payload.belong_DB_module;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.clusterId = payload.clusterId;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.control_area = payload.control_area;
    this.create_time = payload.create_time;
    this.create_user = payload.create_user;
    this.id = payload.id;
    this.instance_name = payload.instance_name;
    this.master_enter = payload.master_enter;
    this.operation = payload.operation;
    this.proxies = payload.proxies || [];
    this.slave_enter = payload.slave_enter;
    this.status = payload.status;
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.create_time).add(24, 'hour'));
  }

  get dbStatusConfigureObj() {
<<<<<<< HEAD
    const text = SqlServerCluster.statusMap[this.status] || '--';
    const theme = SqlServerCluster.themes[this.status] || 'danger';
    return {
      text,
      theme,
    };
=======
    const text = SQLServerClusterList.statusMap[this.status] || '--';
    const theme = SQLServerClusterList.themes[this.status] || 'danger';
    return { text, theme };
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  }
}
