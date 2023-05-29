package monitor_item_interface

// MonitorItemInterface TODO
type MonitorItemInterface interface {
	Run() (msg string, err error)
	Name() string
}

// MonitorItemConstructorFuncType TODO
type MonitorItemConstructorFuncType func(cc *ConnectionCollect) MonitorItemInterface
