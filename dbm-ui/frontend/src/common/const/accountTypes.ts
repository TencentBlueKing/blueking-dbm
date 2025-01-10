/**
 * 账号类型
 */
export enum AccountTypes {
  MONGODB = 'mongodb',
  MYSQL = 'mysql',
  SQLSERVER = 'sqlserver',
  TENDBCLUSTER = 'tendbcluster',
}
export type AccountTypesValues = `${AccountTypes}`;
