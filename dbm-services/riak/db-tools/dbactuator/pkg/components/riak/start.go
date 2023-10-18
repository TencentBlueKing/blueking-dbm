// Package riak TODO
/*
 * @Description: 安装 Riak
 */
package riak

// StartComp TODO
type StartComp struct {
	Params          *StartParam `json:"extend"`
	StartRunTimeCtx `json:"-"`
}

// StartParam TODO
type StartParam struct {
}

// StartRunTimeCtx 运行时上下文
type StartRunTimeCtx struct {
}

// Start 启动
func (i *StartComp) Start() error {
	return Start()
}
