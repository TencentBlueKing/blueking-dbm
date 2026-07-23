package checker

import (
	"fmt"
	"time"

	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

// PtExitFlagMap pt-table-check 退出位映射
var PtExitFlagMap map[int]PtExitFlag

// Mode 模式变量
var Mode config.CheckMode

var commonForceSwitchStrategies []switchStrategy
var commonDefaultSwitchStrategies []switchStrategy
var generalForceSwitchStrategies []switchStrategy
var generalDefaultSwitchStrategies []switchStrategy
var demandForceSwitchStrategies []switchStrategy
var demandDefaultSwitchStrategies []switchStrategy
var dtsForceSwitchStrategies []switchStrategy
var dtsDefaultSwitchStrategies []switchStrategy

var commonDefaultKVStrategies []kvStrategy
var commonForceKVStrategies []kvStrategy
var generalDefaultKVStrategies []kvStrategy
var generalForceKVStrategies []kvStrategy
var demandDefaultKVStrategies []kvStrategy
var demandForceKVStrategies []kvStrategy
var dtsDefaultKVStrategies []kvStrategy
var dtsForceKVStrategies []kvStrategy

func init() {
	PtExitFlagMap = map[int]PtExitFlag{
		1:  {Flag: "ERROR", BitValue: 1, Meaning: "A non-fatal error occurred"},
		2:  {Flag: "ALREADY_RUNNING", BitValue: 2, Meaning: "--pid file exists and the PID is running"},
		4:  {Flag: "CAUGHT_SIGNAL", BitValue: 4, Meaning: "Caught SIGHUP, SIGINT, SIGPIPE, or SIGTERM"},
		8:  {Flag: "NO_SLAVES_FOUND", BitValue: 8, Meaning: "No replicas or cluster nodes were found"},
		16: {Flag: "TABLE_DIFF", BitValue: 16, Meaning: "At least one diff was found"},
		32: {Flag: "SKIP_CHUNK", BitValue: 32, Meaning: "At least one chunk was skipped"},
		64: {Flag: "SKIP_TABLE", BitValue: 64, Meaning: "At least one table was skipped"},
	}

	/*
		各种场景下的参数约束
		没有做什么优先级, 所以 general, demand 的 配置不要和 common 重复
		有很多和安全相关的参数这里没有出现, 不代表那些参数没有用, 而是默认值刚好非常合适
	*/
	commonForceSwitchStrategies = []switchStrategy{
		{Name: "check-binlog-format", Value: true, HasOpposite: true},
		{Name: "check-replication-filters", Value: false, HasOpposite: true},
		{Name: "quiet", Value: false, HasOpposite: false},
		{Name: "binary-index", Value: true, HasOpposite: false},
		{Name: "version-check", Value: false, HasOpposite: true},
		{Name: "create-replicate-table", Value: true, HasOpposite: true},
	}
	commonDefaultSwitchStrategies = []switchStrategy{}
	commonForceKVStrategies = []kvStrategy{
		// kv 中不允许出现 replicate, 只能在 pt_checksum.replicate 中指定
		{Name: "replicate", Value: nil, Enable: false},
		// kv 中不允许出现库表过滤, 只能在 Filter 中定义
		{Name: "databases", Value: nil, Enable: false},
		{Name: "tables", Value: nil, Enable: false},
		{Name: "ignore-databases", Value: nil, Enable: false},
		{Name: "ignore-tables", Value: nil, Enable: false},
		{Name: "databases-regex", Value: nil, Enable: false},
		{Name: "tables-regex", Value: nil, Enable: false},
		{Name: "ignore-databases-regex", Value: nil, Enable: false},
		{Name: "ignore-tables-regex", Value: nil, Enable: false},
	}
	commonDefaultKVStrategies = []kvStrategy{
		{
			Name: "chunk-size-limit",
			Value: func(checker *Checker) interface{} {
				return 5
			},
			Enable: true,
		},
		{
			Name: "chunk-time",
			Value: func(checker *Checker) interface{} {
				return 1
			},
			Enable: true,
		},
		{
			Name: "progress",
			Value: func(checker *Checker) interface{} {
				return "time,864000"
			},
			Enable: true,
		},
		{
			Name: "max-load",
			Value: func(checker *Checker) interface{} {
				return "Threads_running=500"
			},
			Enable: true,
		},
	}

	/*
		例行校验的个性化配置
		例行校验不要增加和 slave check 相关的任何参数
		因为目前没有可靠的办法提供从 master 以 select 访问 slave 的帐号
	*/
	generalForceSwitchStrategies = []switchStrategy{
		{Name: "resume", Value: true, HasOpposite: false},
		// no-replicate-check：关闭 pt 每表跑完后在 slave replicate 表上比 this_crc/master_crc（查数据不一致）。
		// 不是 SHOW SLAVE STATUS / IO·SQL 线程监控；与 dbactuator checkSlaveStatus 不是一回事。
		{Name: "replicate-check", Value: false, HasOpposite: true},
		// {Name: "check-slave-tables", Value: false, HasOpposite: true},
	}
	generalDefaultSwitchStrategies = []switchStrategy{}
	generalForceKVStrategies = []kvStrategy{
		{
			Name: "recursion-method",
			Value: func(checker *Checker) interface{} {
				return "none"
			},
			Enable: true,
		},
	}
	generalDefaultKVStrategies = []kvStrategy{
		{
			Name: "run-time",
			Value: func(checker *Checker) interface{} {
				return time.Hour * 2
			},
			Enable: true,
		},
	}

	/*
		单据校验的个性化配置
	*/
	demandForceSwitchStrategies = []switchStrategy{
		{Name: "resume", Value: false, HasOpposite: false},
		// no-replicate-check：同上，不做 per-table crc diff；不能替代复制线程健康检查。
		{Name: "replicate-check", Value: false, HasOpposite: true},
	}
	demandDefaultSwitchStrategies = []switchStrategy{}
	demandForceKVStrategies = []kvStrategy{
		{
			Name: "recursion-method",
			Value: func(checker *Checker) interface{} {
				return fmt.Sprintf("dsn=D=%s,t=dsns", checker.resultDB)
			},
			Enable: true,
		},
	}
	demandDefaultKVStrategies = []kvStrategy{
		{
			Name: "run-time",
			Value: func(checker *Checker) interface{} {
				return time.Hour * 48
			},
			Enable: true,
		},
		{
			// max-lag：pt 读 Seconds_Behind_Master，超过阈值则暂停 checksum 等待追上。
			// slave 停/copy 线程挂时 lag 可能为 NULL，pt 会打印 "Replica is stopped. Waiting." 一直等，不会 fail。
			// 不是 IO/SQL Running 监控；复制断了要快停靠 dbactuator DoChecksumV2 的 checkSlaveStatus。
			Name: "max-lag",
			Value: func(checker *Checker) interface{} {
				return 10
			},
			Enable: true,
		},
	}
	/*
		dts 模式校验
	*/
	dtsForceSwitchStrategies = []switchStrategy{
		{Name: "resume", Value: false, HasOpposite: false},
		// no-replicate-check：同上，不做 per-table crc diff；不能替代复制线程健康检查。
		{Name: "replicate-check", Value: false, HasOpposite: true},
	}
	dtsDefaultSwitchStrategies = []switchStrategy{}
	dtsForceKVStrategies = []kvStrategy{
		{
			Name: "recursion-method",
			Value: func(checker *Checker) interface{} {
				return "none"
			},
			Enable: true,
		},
	}
	dtsDefaultKVStrategies = []kvStrategy{
		{
			Name: "run-time",
			Value: func(checker *Checker) interface{} {
				return time.Hour * 48
			},
			Enable: true,
		},
	}
}
