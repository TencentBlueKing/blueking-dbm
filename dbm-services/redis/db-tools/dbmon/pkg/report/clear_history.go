package report

import (
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/util"

	"go.uber.org/zap"
)

// GlobHistoryClearJob global var
var GlobHistoryClearJob *HistoryClearJob

// HistoryClearJob 清理历史report记录
type HistoryClearJob struct {
	Conf *config.Configuration `json:"conf"`
}

// InitGlobalHistoryClearJob new
func InitGlobalHistoryClearJob(conf *config.Configuration) {
	GlobHistoryClearJob = &HistoryClearJob{
		Conf: conf,
	}
}

// Run run
func (job *HistoryClearJob) Run() {
	mylog.Logger.Info("historyClear wakeup,start running...", zap.String("conf", util.ToString(job.Conf)))
	defer mylog.Logger.Info("historyClear end running")
	job.ClearRedisHistoryReport()
}

// ClearRedisHistoryReport 清理redis历史report记录
func (job *HistoryClearJob) ClearRedisHistoryReport() (err error) {
	var clearCmd string
	redisReportPath := filepath.Join(job.Conf.GsePath, "redis")
	if !util.FileExists(redisReportPath) {
		return
	}
	clearCmd = fmt.Sprintf(
		`cd %s && find ./ -type f -regex '.*\.log$' -mtime +%d -exec rm -f {} \;`,
		redisReportPath, job.Conf.ReportLeftDay)
	mylog.Logger.Info(clearCmd)
	_, err = util.RunBashCmd(clearCmd, "", nil, 1*time.Hour)
	return
}
