/**
 * 批量操作计数结果
 * - n：已选集群总数
 * - k：将提交数量
 * - a：无权限跳过数量
 * - b：状态不符跳过数量
 * - s：跳过总数（= a + b）
 */
export interface BatchOperationCount {
  a: number;
  b: number;
  k: number;
  n: number;
  s: number;
}

/**
 * 批量操作的权限/状态判定谓词
 */
export interface BatchOperationPredicate<T> {
  /** 对该操作是否有权限，false 计入无权限 a */
  hasPermission: (item: T) => boolean;
  /** 有权限但状态不符（如已禁用再禁用），true 计入状态不符 b */
  statusMismatch: (item: T) => boolean;
}

/**
 * 批量操作计数：一行只算一次，按「无权限 → 状态不符 → 其余」顺序判定，满足即计入。
 * 满足 N=K+S、S=a+b；确认层按打开弹窗时的权限与状态计数。
 */
export function countBatchOperation<T>(
  items: T[],
  { hasPermission, statusMismatch }: BatchOperationPredicate<T>,
): BatchOperationCount {
  const count = items.reduce<Pick<BatchOperationCount, 'k' | 'a' | 'b'>>(
    (acc, item) => {
      if (!hasPermission(item)) {
        Object.assign(acc, { a: acc.a + 1 });
      } else if (statusMismatch(item)) {
        Object.assign(acc, { b: acc.b + 1 });
      } else {
        Object.assign(acc, { k: acc.k + 1 });
      }
      return acc;
    },
    { a: 0, b: 0, k: 0 },
  );
  return {
    n: items.length,
    ...count,
    s: count.a + count.b,
  };
}
