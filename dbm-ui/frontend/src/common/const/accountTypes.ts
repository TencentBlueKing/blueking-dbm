/**
 * 账号类型
 */
export enum AccountTypes {
  MYSQL = 'mysql',
  TENDBCLUSTER = 'tendbcluster',
  MONGODB = 'mongodb',
  SQLSERVER = 'sqlserver',
}
export type AccountTypesValues = `${AccountTypes}`;
