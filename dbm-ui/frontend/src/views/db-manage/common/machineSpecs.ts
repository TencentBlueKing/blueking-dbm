import type { MachineSpec } from '@services/types';

import { DBTypeInfos } from '@common/const';

import { t } from '@locales/index';

/** 机器类型中文名映射（来自 DBTypeInfos.machineList） */
const machineTypeNameMap: Record<string, string> = {};
Object.values(DBTypeInfos).forEach((db) => {
  db.machineList.forEach((machine) => {
    machineTypeNameMap[machine.value] = machine.label;
  });
});

/** 获取机器类型中文名，未匹配时回退原值 */
export const getMachineTypeName = (machineType: string) => machineTypeNameMap[machineType] || machineType;

type SpecStatus = 'disabled' | 'unbound' | 'normal';

const isUnbound = (spec: MachineSpec) =>
  spec.enable === null || spec.spec_ids.length === 0 || spec.spec_name === t('未绑定');

const getSpecStatus = (spec: MachineSpec): SpecStatus => {
  if (spec.enable === false) {
    return 'disabled';
  }
  if (isUnbound(spec)) {
    return 'unbound';
  }
  return 'normal';
};

const statusOrder: Record<SpecStatus, number> = {
  disabled: 0,
  normal: 2,
  unbound: 1,
};

/** 组内排序：仅将已停用 → 未绑定 → 正常 置前；count/spec_name 顺序由后端已按 (machine_type + count 倒序 + spec_name) 排好，前端不再重复排序（稳定排序保持后端相对顺序） */
export const sortMachineSpecs = (specs: MachineSpec[]) =>
  [...specs].sort((a, b) => statusOrder[getSpecStatus(a)] - statusOrder[getSpecStatus(b)]);

/** 列表代表：后端已按 count 倒序 + spec_name 升序排列，同角色第一条即代表（台数最多，台数相同取规格名升序第一条） */
export const selectRepresentative = (specs: MachineSpec[]) => specs[0];

export interface MachineSpecGroup {
  machineType: string;
  /** 列表代表 */
  representative: MachineSpec;
  roleName: string;
  /** 组内按展示规则排序后的全量（tooltip / 详情使用） */
  specs: MachineSpec[];
}

/** 按 machine_type 分组，组内排序并计算代表 */
export const groupMachineSpecs = (specs: MachineSpec[]): MachineSpecGroup[] => {
  const groupMap = new Map<string, MachineSpec[]>();
  specs.forEach((spec) => {
    const list = groupMap.get(spec.machine_type) || [];
    list.push(spec);
    groupMap.set(spec.machine_type, list);
  });

  return [...groupMap.entries()].map(([machineType, list]) => ({
    machineType,
    representative: selectRepresentative(list),
    roleName: getMachineTypeName(machineType),
    specs: sortMachineSpecs(list),
  }));
};
