import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.DbRename>) =>
  ticketDetail.details.infos.map((item) => ({
    cluster_id: item.cluster_id,
    cluster: ticketDetail.details.clusters[item.cluster_id],
    from_database: item.from_database,
    to_database: item.to_database,
  }));
