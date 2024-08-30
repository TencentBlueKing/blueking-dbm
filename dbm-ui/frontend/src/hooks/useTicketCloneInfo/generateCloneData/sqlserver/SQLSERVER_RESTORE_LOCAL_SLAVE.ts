import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.RestoreLocalSlave>) =>
  ticketDetail.details.infos.map((item) => ({
    cluster: ticketDetail.details.clusters[item.cluster_id],
    slave: item.slave,
  }));
