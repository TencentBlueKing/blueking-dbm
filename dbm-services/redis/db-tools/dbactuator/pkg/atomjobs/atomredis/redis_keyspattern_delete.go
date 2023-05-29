package atomredis

import "dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"

// TendisKeysPatternDelete 按正则删除key,这里会有很多代码和TendisKeysPattern一样
// 所以在 TendisKeysPattern 里实现按正则删除key，为了flow区分，加了tendis_keysdelete_regex 原子任务
type TendisKeysPatternDelete struct {
	TendisKeysPattern
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*TendisKeysPatternDelete)(nil)

// NewTendisKeysPatternDelete  new
func NewTendisKeysPatternDelete() jobruntime.JobRunner {
	return &TendisKeysPatternDelete{}
}

// Name 原子任务名
func (job *TendisKeysPatternDelete) Name() string {
	return "tendis_keysdelete_regex"
}
