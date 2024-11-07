import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.ImportSqlFile>) => {
  const { details } = ticketDetail;
  return {
    backup: details.backup,
    backup_place: details.backup_place,
    charset: details.charset,
    cluster_ids: details.cluster_ids,
    cluster: details.cluster_ids.map((item) => details.clusters[item]),
    execute_objects: details.execute_objects,
    file_tag: 'DBFILE1M',
    force: details.force,
    path: details.path,
    ticket_mode: details.ticket_mode,
    remark: ticketDetail.remark,
  };
};
