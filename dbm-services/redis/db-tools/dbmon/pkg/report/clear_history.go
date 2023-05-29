package report

import (
	"fmt"
	"path/filepath"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/util"

	"go.uber.org/zap"
)

// globHistoryClearJob global var
var globHistoryClearJob *HistoryClearJob
var clearOnce sync.Once

// HistoryClearJob 清理历史report记录
type HistoryClearJob struct {
	Conf *config.Configuration `json:"conf"`
}

// GetGlobalHistoryClearJob new
func GetGlobalHistoryClearJob(conf *config.Configuration) *HistoryClearJob {
	clearOnce.Do(func() {
		globHistoryClearJob = &HistoryClearJob{
			Conf: conf,
		}
	})
	return globHistoryClearJob
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
	redisReportPath := filepath.Join(job.Conf.ReportSaveDir, "redis")
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
