import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.DataMigrate>) =>
  ticketDetail.details.infos.map((item) => ({
    db_list: item.db_list,
    dst_cluster: ticketDetail.details.clusters[item.dst_cluster],
    dts_id: item.dts_id,
    ignore_db_list: item.ignore_db_list,
    rename_infos: item.rename_infos,
    src_cluster: ticketDetail.details.clusters[item.src_cluster],
  }));
