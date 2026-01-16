import dayjs from 'dayjs';

import type { ClusterTypes } from '@common/const';

import { getCostTimeDisplay, utcDisplayTime } from '@utils';

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
