import { DBTypeInfos, DBTypes } from '@common/const';

/**
 * 获取某数据库类型对应的 DBA 告警组 label（固定格式：`${名称}_DBA`）
 */
export const getDbaLabel = (dbType: DBTypes) => `${DBTypeInfos[dbType].name}_DBA`;
