/**
 * 资源池类型枚举值
 */
export enum ResourcePool {
  public = 'public',
  global = 'global',
  business = 'business',
}

/**
 * 资源池类型
 */
export type ResourcePoolType = ResourcePool.business | ResourcePool.global | ResourcePool.public;
