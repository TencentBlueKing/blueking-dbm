package basejob

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"sync"

	"go.uber.org/zap"
)

// BaseJob  任务基类 用于处理配置文件读取，更新
type BaseJob struct { // NOCC:golint/naming(其他:设计如此)
	Name         string
	Conf         *config.DbMonConfig   // 全局配置，数据源是配置文件，可能会被更新
	MyConf       *config.Configuration // 任务内部使用的配置，是Conf.Config的副本
	Logger       *zap.Logger
	Err          error
	OsCtx        context.Context // OsCtx Os信号
	RootWg       *sync.WaitGroup // Wg 用于等待任务结束
	rootWgStatus int             // Wg.Done()是否已经调用
	rootWgLock   sync.Mutex
	LoopTimes    uint64 // 循环次数
	WorkDir      string // 工作目录
}

// UpdateConf 更新配置文件
func (basejob *BaseJob) UpdateConf() error {
	// todo 如果版本号不一致，需要重新加载配置文件
	myConf, err := basejob.Conf.GetCopy()
	basejob.Logger.Debug("UpdateConf", zap.Error(err))
	if err != nil {
		return err
	} else {
		basejob.MyConf = myConf
		return nil
	}
}

const (
	WgStatusInit = iota
	WgStatusRunning
	WgStatusDone
)

// RootWgInit 对RootWg进行初始化
func (basejob *BaseJob) RootWgInit() {
	if basejob.RootWg == nil || basejob.rootWgStatus != WgStatusInit {
		return
	}
	basejob.rootWgLock.Lock()
	defer basejob.rootWgLock.Unlock()
	basejob.Logger.Info("debug: RootWgInit")
	basejob.rootWgStatus = WgStatusRunning
	basejob.RootWg.Add(1)

}

// WatchOsCtx  等待结束信号
func (basejob *BaseJob) WatchOsCtx() bool {
	select {
	case <-basejob.OsCtx.Done():
		return true
	default:
		return false
	}
}

// RootWgDone  wg.done
func (basejob *BaseJob) RootWgDone() {
	if basejob.rootWgStatus == WgStatusRunning {
		basejob.rootWgLock.Lock()
		defer basejob.rootWgLock.Unlock()
		if basejob.rootWgStatus == WgStatusRunning {
			basejob.Logger.Info("debug: RootWgDone")
			basejob.rootWgStatus = WgStatusDone
			basejob.RootWg.Done()
		}
	}
}
