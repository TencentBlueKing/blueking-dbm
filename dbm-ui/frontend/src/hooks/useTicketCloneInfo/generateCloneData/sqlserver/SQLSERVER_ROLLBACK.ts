import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.Rollback>) => ({
  infos: ticketDetail.details.infos,
  is_local: ticketDetail.details.is_local,
});
