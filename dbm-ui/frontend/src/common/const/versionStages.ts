/**
 * 版本阶段，按从早到晚排列，表格 tag、编辑表单、搜索栏候选项都由此派生
 */
export interface VersionStage {
  label: string;
  theme: 'danger' | 'warning' | 'info' | 'success';
  value: string;
}

export const versionStageList: VersionStage[] = [
  {
    label: 'Alpha',
    theme: 'danger',
    value: 'alpha',
  },
  {
    label: 'Beta',
    theme: 'warning',
    value: 'beta',
  },
  {
    label: 'RC',
    theme: 'info',
    value: 'rc',
  },
  {
    label: 'Release',
    theme: 'success',
    value: 'release',
  },
];

/**
 * 按阶段值索引的版本阶段
 */
export const versionStageMap = versionStageList.reduce<Record<string, VersionStage>>(
  (result, item) => Object.assign(result, { [item.value]: item }),
  {},
);
