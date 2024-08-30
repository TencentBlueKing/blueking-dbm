import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.RestoreSlave>) =>
  ticketDetail.details.infos.map((item) => ({
    cluster_ids: item.cluster_ids,
    clusters: item.cluster_ids.map((item) => ticketDetail.details.clusters[item]),
    new_slave_host: item.new_slave_host,
    old_slave_host: item.old_slave_host,
    system_version: item.system_version,
  }));
