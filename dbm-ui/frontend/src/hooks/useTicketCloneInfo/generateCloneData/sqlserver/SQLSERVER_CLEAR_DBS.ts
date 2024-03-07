import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.ClearDbs>) =>
  ticketDetail.details.infos.map((item) => ({
    clean_dbs: item.clean_dbs,
    clean_dbs_patterns: item.clean_dbs_patterns,
    clean_ignore_dbs_patterns: item.clean_ignore_dbs_patterns,
    clean_mode: item.clean_mode,
    clean_tables: item.clean_tables,
    cluster_id: item.cluster_id,
    cluster: ticketDetail.details.clusters[item.cluster_id],
    ignore_clean_tables: item.ignore_clean_tables,
  }));
