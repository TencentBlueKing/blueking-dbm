package impl

import (
	"errors"
	"slices"

	"github.com/go-sql-driver/mysql"
)

// txFatalErrNum 这些错误一旦在事务中出现, server 会回滚事务 (或事务已无法继续).
// 即使调用方设置了 Force=true, 后续 SQL 也不应该再发送; 否则结果不可预期.
var txFatalErrNum = []uint16{
	1205, // ER_LOCK_WAIT_TIMEOUT: 当 innodb_rollback_on_timeout=ON 时整事务回滚
	1213, // ER_LOCK_DEADLOCK: InnoDB 检测到死锁, 自动回滚整事务
	1614, // ER_XA_RBDEADLOCK: XA 事务因死锁被回滚
}

// IsTransactionFatalError 判断是否是"会让当前事务失效"的错误.
//
// 这类错误一旦发生, 当前 server 端事务已经/即将被自动回滚, 后续在同一 batch
// 里的 SQL 即使继续发出去也无法回到一致状态. 因此即使调用方传了 Force=true,
// 也必须立即中止整个 batch, 让上层感知到事务已经失败.
func IsTransactionFatalError(err error) (bool, *mysql.MySQLError) {
	var me *mysql.MySQLError
	if errors.As(err, &me) && slices.Index(txFatalErrNum, me.Number) >= 0 {
		return true, me
	}
	return false, nil
}
