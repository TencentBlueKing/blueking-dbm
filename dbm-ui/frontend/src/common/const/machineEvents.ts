import { t } from '@locales/index';

/**
 * 机器事件统类型
 */
export const enum MachineEvents {
  IMPORT_RESOURCE = 'import_resource',
  APPLY_RESOURCE = 'apply_resource',
  RETURN_RESOURCE = 'return_resource',
  TO_DIRTY = 'to_dirty',
  TO_RECYCLE = 'to_recycle',
  TO_FAULT = 'to_fault',
  UNDO_IMPORT = 'undo_import',
  RECYCLED = 'recycled',
}

export const machineEventsDisplayMap = {
  [MachineEvents.IMPORT_RESOURCE]: t('导入资源池'),
  [MachineEvents.APPLY_RESOURCE]: t('申请资源'),
  [MachineEvents.RETURN_RESOURCE]: t('退回资源'),
  [MachineEvents.TO_DIRTY]: t('转入污点池'),
  [MachineEvents.TO_RECYCLE]: t('转入待回收池'),
  [MachineEvents.TO_FAULT]: t('转入故障池'),
  [MachineEvents.UNDO_IMPORT]: t('撤销导入'),
  [MachineEvents.RECYCLED]: t('回收'),
};
