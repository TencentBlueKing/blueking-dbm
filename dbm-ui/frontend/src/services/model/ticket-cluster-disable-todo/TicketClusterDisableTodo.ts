import dayjs from 'dayjs';

import { ClusterTypes } from '@common/const';

import { getCostTimeDisplay, utcDisplayTime } from '@utils';

import { t } from '@/locales';

export default class TicketClusterDisableTodo {
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_type: ClusterTypes;
  disable_person: string;
  disable_time: string;
  id: number;
  immute_domain: string;
  major_version: string;
  name: string;
  region: string;

  constructor(payload = {} as TicketClusterDisableTodo) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.disable_person = payload.disable_person;
    this.disable_time = payload.disable_time;
    this.immute_domain = payload.immute_domain;
    this.major_version = payload.major_version;
    this.cluster_type = payload.cluster_type;
    this.id = payload.id;
    this.name = payload.name;
    this.region = payload.region;
  }

  get clusterTypesDisplay() {
    if (
      [
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ].includes(this.cluster_type)
    ) {
      return t('集群');
    }
    const textMap = {
      [ClusterTypes.MONGO_REPLICA_SET]: t('副本集'),
      [ClusterTypes.MONGO_SHARED_CLUSTER]: t('分片集群'),
      [ClusterTypes.REDIS_INSTANCE]: t('主从'),
      [ClusterTypes.SQLSERVER_HA]: t('主从'),
      [ClusterTypes.SQLSERVER_SINGLE]: t('单节点'),
      [ClusterTypes.TENDBHA]: t('主从'),
      [ClusterTypes.TENDBSINGLE]: t('单节点'),
    };

    return textMap[this.cluster_type as keyof typeof textMap] || '';
  }

  get disableSecondsDisplay() {
    const disableTime = dayjs.utc(this.disable_time);
    const secondDiff = dayjs().diff(disableTime, 'second');
    return getCostTimeDisplay(secondDiff);
  }

  get distableTimeDisplay() {
    return utcDisplayTime(this.disable_time);
  }

  get isDisableAlert() {
    const disableTime = dayjs.utc(this.disable_time);
    return dayjs().isAfter(disableTime.add(7, 'day'));
  }
}
