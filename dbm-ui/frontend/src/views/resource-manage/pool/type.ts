/**
 * 资源池类型枚举值
 */
export enum ResourcePool {
  business = 'business',
  global = 'global',
  public = 'public',
}

/**
 * 资源池类型
 */
export type ResourcePoolType = ResourcePool.business | ResourcePool.global | ResourcePool.public;
