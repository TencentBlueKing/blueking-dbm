import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.Rollback>) => ({
  infos: ticketDetail.details.infos.map((item) => ({
    db_list: item.db_list,
    dst_cluster: ticketDetail.details.clusters[item.dst_cluster],
    ignore_db_list: item.ignore_db_list,
    rename_infos: item.rename_infos,
    restore_backup_file: item.restore_backup_file,
    src_cluster: ticketDetail.details.clusters[item.src_cluster],
  })),
  is_local: ticketDetail.details.is_local,
});
