import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.BackupDb>) => ({
  backup_place: ticketDetail.details.backup_place,
  backup_type: ticketDetail.details.backup_type,
  file_tag: ticketDetail.details.file_tag,
  info: ticketDetail.details.infos.map((item) => ({
    backup_dbs: item.backup_dbs,
    cluster_id: item.cluster_id,
    cluster: ticketDetail.details.clusters[item.cluster_id],
    db_list: item.db_list,
    ignore_db_list: item.ignore_db_list,
  })),
});
