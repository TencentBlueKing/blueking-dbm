import { t } from '@locales/index';

/**
 * 机器事件统类型
 */
export const enum MachineEvents {
  APPLY_RESOURCE = 'apply_resource',
  IMPORT_RESOURCE = 'import_resource',
  RECYCLED = 'recycled',
  RETURN_RESOURCE = 'return_resource',
  TO_DIRTY = 'to_dirty',
  TO_FAULT = 'to_fault',
  TO_RECYCLE = 'to_recycle',
  UNDO_IMPORT = 'undo_import',
}

export const machineEventsDisplayMap = {
  [MachineEvents.APPLY_RESOURCE]: t('申请资源'),
  [MachineEvents.IMPORT_RESOURCE]: t('导入资源池'),
  [MachineEvents.RECYCLED]: t('主机回收'),
  [MachineEvents.RETURN_RESOURCE]: t('退回资源池'),
  [MachineEvents.TO_DIRTY]: t('转入污点池'),
  [MachineEvents.TO_FAULT]: t('转入故障池'),
  [MachineEvents.TO_RECYCLE]: t('转入待回收池'),
  [MachineEvents.UNDO_IMPORT]: t('撤销导入'),
};
