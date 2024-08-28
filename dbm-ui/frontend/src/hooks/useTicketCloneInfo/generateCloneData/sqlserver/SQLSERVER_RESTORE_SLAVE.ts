import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

export default async (ticketDetail: TicketModel<Sqlserver.RestoreSlave>) =>
  ticketDetail.details.infos.map((item) => ({
    new_slave_host: item.new_slave_host,
    old_slave_host: item.old_slave_host,
  }));
