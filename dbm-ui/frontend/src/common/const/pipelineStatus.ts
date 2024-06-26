/**
 * 管道状态
 */
export enum PipelineStatus {
  READY = 'READY', // 准备中
  RUNNING = 'RUNNING', // 运行中
  FINISHED = 'FINISHED', // 完成
  FAILED = 'FAILED', // 失败
}
