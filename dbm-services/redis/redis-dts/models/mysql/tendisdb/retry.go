package tendisdb

import (
	"fmt"
	"math/rand"
	"strings"
	"time"

	"go.uber.org/zap"
)

// 瞬时错误重试配置。
// 双重上限：次数上限防止死循环,时间上限防止调度循环被长时间阻塞。
// 退避节奏: 10s -> 20s -> 40s -> 80s(封顶),只要其中一次成功即视为成功。
const (
	// getTaskRetryMaxAttempts GetTaskByID 的最大尝试次数(含首次),超过则直接返回错误
	getTaskRetryMaxAttempts = 5
	// getTaskRetryMaxBackoff 累计退避时长上限,超过则直接返回错误
	getTaskRetryMaxBackoff = 3 * time.Minute
	// getTaskRetryInitialBackoff 首次退避基准: 10s;后续翻倍(20s/40s/80s),封顶 singleMaxBackoff
	getTaskRetryInitialBackoff = 10 * time.Second
	// getTaskRetryMaxSingleBackoff 单次最大退避: 80s
	getTaskRetryMaxSingleBackoff = 80 * time.Second
)

// transientBizCodeWhitelist 业务错误码白名单。
// 这些错误来自上游(典型为 bkDbm),表示后端瞬时不可用,客户端重试有望成功。
// 8700500: SQLAlchemy 连接池打满 / 系统错误(用户报错的根因)
var transientBizCodeWhitelist = []string{
	"code:8700500",
}

// transientErrKeywords 错误信息关键字,命中即视为瞬时错误
var transientErrKeywords = []string{
	"QueuePool limit",      // SQLAlchemy 池满: QueuePool limit of size 20 overflow 200 reached
	"connection timed out", // 网络 / DB 超时
	"context deadline exceeded",
	"i/o timeout",
	"connection reset",
	"connection refused",
	"no such host",
	"EOF", // 服务端异常断开
}

// isTransientErr 判断 err 是否属于"可重试的瞬时错误"。
// 设计原则:
//   - 只对配置白名单内的业务错误码 / 明确的瞬时网络错误做重试;
//   - 其他错误(如 4xx 参数错误、其他业务码)直接返回失败,不浪费重试预算。
func isTransientErr(err error) bool {
	if err == nil {
		return false
	}
	s := err.Error()
	// 业务码白名单
	for _, code := range transientBizCodeWhitelist {
		if strings.Contains(s, code) {
			return true
		}
	}
	// 瞬时关键字
	for _, kw := range transientErrKeywords {
		if strings.Contains(s, kw) {
			return true
		}
	}
	return false
}

// retryOnTransient 在 fn 返回的 err 是瞬时错误时,按指数退避重试 fn。
// 同时受"次数上限"和"累计退避时间上限"双重约束,任一达到即停止重试并返回最后一次错误。
// 非瞬时错误立即返回,不消耗重试预算。
//
// 参数:
//   - maxAttempts: 最大尝试次数(含首次)
//   - maxBackoff:  累计退避时长上限(达到后不再 sleep,直接返回)
//   - initialBackoff: 首次退避,后续每次翻倍,封顶 singleMaxBackoff
//   - singleMaxBackoff: 单次退避封顶
//   - opName: 用于日志的算子描述
//   - fn: 被重试的调用,返回 error
//   - logger: zap logger,可为 nil(为 nil 时不输出 warn 日志)
func retryOnTransient(
	maxAttempts int,
	maxBackoff time.Duration,
	initialBackoff time.Duration,
	singleMaxBackoff time.Duration,
	opName string,
	fn func() error,
	logger *zap.Logger,
) error {
	if maxAttempts <= 0 {
		maxAttempts = 1
	}
	var (
		totalBackoff time.Duration
		sleepDur     = initialBackoff
	)
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		err := fn()
		if err == nil {
			return nil
		}
		// 非瞬时错误: 立即失败,不消耗重试预算
		if !isTransientErr(err) {
			return err
		}
		// 最后一次尝试: 不再 sleep,直接返回
		if attempt == maxAttempts {
			logTransientWarn(logger, opName, attempt, maxAttempts, sleepDur, totalBackoff,
				fmt.Sprintf("transient err, attempts exhausted, give up: %v", err))
			return err
		}
		// 时间预算耗尽: 直接返回错误
		if totalBackoff+sleepDur > maxBackoff {
			logTransientWarn(logger, opName, attempt, maxAttempts, sleepDur, totalBackoff,
				fmt.Sprintf("transient err, maxBackoff=%s reached, give up: %v", maxBackoff, err))
			return err
		}
		// 加入抖动(等比抖动: [0.5*sleepDur, 1.5*sleepDur)),避免大量并发调用
		// (如同时有几十个DTS任务在轮询状态)在同一时刻被打满连接池后,
		// 又在完全相同的时刻集中重试,造成"重试风暴"反复把连接池打满。
		jitteredSleep := jitter(sleepDur)
		logTransientWarn(logger, opName, attempt, maxAttempts, jitteredSleep, totalBackoff,
			fmt.Sprintf("transient err, sleep %s(base %s) and retry: %v", jitteredSleep, sleepDur, err))
		time.Sleep(jitteredSleep)
		totalBackoff += jitteredSleep
		// 指数退避,封顶 singleMaxBackoff
		sleepDur *= 2
		if sleepDur > singleMaxBackoff {
			sleepDur = singleMaxBackoff
		}
	}
	return nil
}

// jitter 对退避时长 d 做等比抖动,返回值落在 [0.5d, 1.5d) 区间。
// 目的: 大量并发调用如果都用完全相同的固定退避序列,一旦同时因连接池打满而失败,
// 会在完全相同的时刻发起下一轮重试,形成同步的"重试风暴",反而更难恢复;
// 加入随机抖动后,各调用方的重试时刻被打散,能更平滑地分摊到上游服务上。
func jitter(d time.Duration) time.Duration {
	if d <= 0 {
		return d
	}
	half := d / 2
	// [0, half) 的随机量 + half,得到 [half, 2*half)=[0.5d,1.5d) 区间(整数除法误差可忽略)
	return half + time.Duration(rand.Int63n(int64(half)+1))
}

func logTransientWarn(logger *zap.Logger, opName string, attempt, maxAttempts int,
	sleepDur, totalBackoff time.Duration, msg string) {
	if logger == nil {
		return
	}
	logger.Warn(fmt.Sprintf("[%s] %s attempt=%d/%d, sleep=%s, totalBackoff=%s",
		opName, msg, attempt, maxAttempts, sleepDur, totalBackoff))
}
