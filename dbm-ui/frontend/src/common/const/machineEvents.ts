import { t } from '@locales/index';

/**
 * 机器事件统类型
 */
export const enum MachineEvents {
  APPLY_RESOURCE = 'apply_resource',
  HCM_REMOVE = 'hcm_remove',
  HOST_ATTRIBUTE = 'host_attribute',
  IMPORT_RESOURCE = 'import_resource',
  RECYCLED = 'recycled',
  REMOVE_HOST = 'remove_host',
  RESOURCE_OWNER = 'resource_owner',
  RETURN_RESOURCE = 'return_resource',
  // TO_DIRTY = 'to_dirty',
  TO_FAULT = 'to_fault',
  TO_RECYCLE = 'to_recycle',
  UNDO_IMPORT = 'undo_import',
}

export const machineEventsDisplayMap = {
  [MachineEvents.APPLY_RESOURCE]: t('资源池申领主机'),
  [MachineEvents.HCM_REMOVE]: t('主机回收'),
  [MachineEvents.HOST_ATTRIBUTE]: t('修改主机属性'),
  [MachineEvents.IMPORT_RESOURCE]: t('导入资源池'),
  [MachineEvents.RECYCLED]: t('主机删除'),
  [MachineEvents.REMOVE_HOST]: t('已下架主机处理'),
  [MachineEvents.RESOURCE_OWNER]: t('修改资源归属'),
  [MachineEvents.RETURN_RESOURCE]: t('退回资源池'),
  // [MachineEvents.TO_DIRTY]: t('转入污点池'),
  [MachineEvents.TO_FAULT]: t('转入故障池'),
  [MachineEvents.TO_RECYCLE]: t('转入待回收池'),
  [MachineEvents.UNDO_IMPORT]: t('撤销导入'),
};

export const machineEventsSelectList = [
  MachineEvents.IMPORT_RESOURCE,
  MachineEvents.APPLY_RESOURCE,
  MachineEvents.RETURN_RESOURCE,
  MachineEvents.TO_FAULT,
  MachineEvents.TO_RECYCLE,
  MachineEvents.REMOVE_HOST,
  MachineEvents.HCM_REMOVE,
  MachineEvents.RECYCLED,
  MachineEvents.UNDO_IMPORT,
  MachineEvents.HOST_ATTRIBUTE,
  MachineEvents.RESOURCE_OWNER,
].map((key) => ({ label: machineEventsDisplayMap[key], value: key }));
