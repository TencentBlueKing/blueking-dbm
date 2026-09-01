export interface MachineSpec {
  /** 主机台数（同机多实例计 1 台） */
  count: number;
  /** 是否启用；未绑定为 null */
  enable: boolean | null;
  /** 主机 IP 列表 */
  ips: string[];
  /** 机器类型（对应 DB 的 MachineType） */
  machine_type: string;
  /** 规格 id 列表；未绑定为空数组 */
  spec_ids: number[];
  /** 规格名；未绑定时为「未绑定」 */
  spec_name: string;
}
