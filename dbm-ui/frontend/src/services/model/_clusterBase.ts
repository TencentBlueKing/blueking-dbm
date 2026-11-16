import _ from 'lodash';

import type { ClusterListNode } from '@services/types';

import type { DBTypeOf, GroupedClusterTypes } from '@common/const';
import { getCloudZoneName } from '@common/const';

import { isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class ClusterBase<T extends GroupedClusterTypes = GroupedClusterTypes> {
  static getRoleFaildInstanceList = (data: ClusterListNode[]) => _.filter(data, (item) => item.status !== 'running');
  /** 地域（集群维度） */
  bk_cloud_region: string;
  /** 可用区（集群维度，名称列表；空数组表示随机） */
  cluster_cloud_zones: string[];
  create_at: string;
  db_type: DBTypeOf<T>;
  id: number;
  phase: string;
  region: string;
  tags: {
    id: number;
    is_builtin: boolean;
    key: string;
    system: boolean;
    value: string;
  }[];
  update_at: string;
  /** 关联集群场景的可用区名列表（find_related_clusters_by_cluster_ids 下发，值同 cluster_cloud_zones） */
  zone_names: string[];

  constructor(payload: ClusterBase<T>) {
    this.bk_cloud_region = payload.bk_cloud_region;
    this.create_at = payload.create_at;
    this.id = payload.id;
    this.db_type = payload.db_type;
    this.phase = payload.phase;
    this.tags = payload.tags || [];
    this.update_at = payload.update_at;
    this.cluster_cloud_zones = payload.cluster_cloud_zones || [];
    this.zone_names = payload.zone_names || [];
    this.region = payload.region;
  }

  get availableTags() {
    return _.sortBy(this.tags, (item) => item.key).filter((item) => !item.system);
  }

  /** 可用区展示值：空值显示「随机」，标识值转前端维护的中文名 */
  get clusterZonesDisplay() {
    if (this.cluster_cloud_zones.length === 0) {
      return t('随机');
    }
    return this.cluster_cloud_zones.map((zoneItem) => getCloudZoneName(zoneItem)).join('，');
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get isNew() {
    return isRecentDays(this.create_at, 24);
  }

  get isOffline() {
    return this.phase === 'offline';
  }

  get isOnline() {
    return this.phase === 'online';
  }

  get masterDomain() {
    // @ts-expect-error 兼容多种集群读取访问入口信息
    return this.master_domain || this.domain || '';
  }

  get regionDisplay() {
    if (!this.bk_cloud_region || this.bk_cloud_region === 'default') {
      return t('随机');
    }
    return this.bk_cloud_region;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
