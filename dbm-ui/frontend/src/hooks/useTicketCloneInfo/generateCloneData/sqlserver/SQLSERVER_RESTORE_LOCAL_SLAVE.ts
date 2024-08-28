import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

import { TicketTypes } from '@common/const';

export interface TicketCloneResult {
  [TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE]: number;
}

export default async (ticketDetail: TicketModel<Sqlserver.RestoreLocalSlave>) =>
  ticketDetail.details.infos.map((item) => ({
    slave: item.slave,
  }));
