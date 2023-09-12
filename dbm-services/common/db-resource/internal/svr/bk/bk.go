// Package bk TODO
package bk

const (
	// GSE_AGENT_OK 运行中
	// Agent当前运行状态码, -1:未知 0:初始安装 1:启动中 2:运行中 3:有损状态 4:繁忙状态 5:升级中 6:停止中 7:解除安装
	GSE_AGENT_OK = 2
	// GSE_AGENT_INSTALLING TODO
	GSE_AGENT_INSTALLING = 0
	// GSE_AGENT_STARTING TODO
	GSE_AGENT_STARTING = 1
	// GSE_AGENT_STATUS_UNKNOWN TODO
	GSE_AGENT_STATUS_UNKNOWN = -1
)
