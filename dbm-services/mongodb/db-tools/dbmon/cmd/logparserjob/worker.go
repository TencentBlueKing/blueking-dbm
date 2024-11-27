package logparserjob

import (
	"context"
	"dbm-services/mongodb/db-tools/dbmon/config"
	"dbm-services/mongodb/db-tools/dbmon/pkg/mongoconf"
	"fmt"
	"path"
	"strconv"
	"sync"
	"time"

	"go.uber.org/zap"
)

func getMongoLogDir(port int, isMongos bool, logger *zap.Logger) string {
	logPath := ""

	if isMongos {
		conf, err := mongoconf.LoadMongosConfig(port)
		if err == nil {
			logPath = conf.SystemLog.Path
		} else {
			logger.Warn(fmt.Sprintf("getMongoLogDir: load mongos config failed: %v", err))
		}
	} else {
		conf, err := mongoconf.LoadMongodConfig(port)
		if err == nil {
			logPath = conf.SystemLog.Path
		} else {
			logger.Warn(fmt.Sprintf("getMongoLogDir: load mongod config failed: %v", err))
		}
	}

	// 如果没有配置文件，使用默认路径
	if logPath == "" {
		defaultPath := path.Join("/data/mongolog", strconv.Itoa(port), "mongo.log")
		logger.Warn(fmt.Sprintf("getMongoLogDir: logPath is empty, use default path: %s", defaultPath))
		logPath = defaultPath
	}
	return logPath
}

// NewWorker 新建worker，用于执行logparser
func NewWorker(server *config.ConfServerItem, maxTime int64, logger *zap.Logger, osCtx context.Context) *Worker {
	mongoLogFile := getMongoLogDir(server.Port, server.MetaRole == "mongos", logger)
	logDir := path.Dir(mongoLogFile)
	jsonDir := path.Join(logDir + "/jsonlog/")
	if maxTime <= 0 {
		logger.Warn("NewWorker: maxTime is 0, set to 300")
		maxTime = 300
	}
	w := &Worker{
		Server:      server,
		Uid:         server.Port,
		LogFilePath: mongoLogFile,
		DstDir:      jsonDir,
		Logger:      logger.With(zap.String("instance", server.Addr())),
		LoopTime:    maxTime,
		OsCtx:       osCtx,
	}

	return w
}

// Worker 执行任务的worker
type Worker struct {
	Server              *config.ConfServerItem
	Uid                 int // port
	LogFilePath, DstDir string
	Wg                  sync.WaitGroup
	Logger              *zap.Logger
	LoopTime            int64 // seconds，每次执行的时间
	Ctx                 context.Context
	CancelFunc          context.CancelFunc
	OsCtx               context.Context
}

const sizeG = 1024 * 1024 * 1024
const secondsDay = 86400

// Run 解析日志文件
func (w *Worker) Run() {
	w.Logger.Info(
		fmt.Sprintf("logFilePattern:%s, outputDir:%s", w.LogFilePath, w.DstDir))

	// rotate log file if size exceeds 1G
	err := w.rotateMongoLog(w.LogFilePath, sizeG*1, int64(float64(w.LoopTime)*1.5))
	if err != nil {
		w.Logger.Error(fmt.Sprintf("rotate log file failed: %v", err))
	}

	w.Ctx, w.CancelFunc = context.WithTimeout(context.Background(), time.Duration(w.LoopTime)*time.Second)
	defer w.CancelFunc()
	succ, fail, err := ParseFile(
		w.LogFilePath, w.DstDir, "mongo.log", true, w.Ctx, w.OsCtx,
		[]byte(w.Server.MetaForLog()), w.Logger)
	w.Logger.Info(fmt.Sprintf("succ %d fail %d err %v", succ, fail, err))
}

// Stop 解析日志文件
func (w *Worker) Stop() {
	w.Logger.Info("stop")
	w.CancelFunc()
}
