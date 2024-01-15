package redistaillog

import (
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/nxadm/tail"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/pkg/report"
	"dbm-services/redis/db-tools/dbmon/util"
)

// BaseSchema schema
type BaseSchema struct {
	BkBizID     string `json:"bk_biz_id"`
	BkCloudID   int64  `json:"bk_cloud_id"`
	ServerIP    string `json:"server_ip"`
	ServerPort  int    `json:"server_port"`
	Domain      string `json:"domain"`
	ClusterType string `json:"cluster_type"`
	Role        string `json:"role"`
}

// Addr addr
func (b *BaseSchema) Addr() string {
	return b.ServerIP + ":" + strconv.Itoa(b.ServerPort)
}

// LogRecordItem item
type LogRecordItem struct {
	BaseSchema
	LogFile    string `json:"log_file"`
	Data       string `json:"data"`
	TimeZone   string `json:"time_zone"`
	CreateTime string `json:"create_time"`
}

// TailTask task
type TailTask struct {
	BaseSchema
	Password      string               `json:"-"`
	rediscli      *myredis.RedisClient `json:"-"`
	NotIncludes   []string             `json:"-"` // 如果包含这些字符串,则不上报
	ReportSaveDir string
	ReportFile    string
	reporter      report.Reporter
	wg            *sync.WaitGroup
	LogFiles      []string
	TailObjs      []*tail.Tail
	done          chan struct{}
	Err           error `json:"-"`
}

// NewTailTask new
func NewTailTask(conf config.ConfServerItem, reportDir string, server_port int) (ret *TailTask,
	err error) {
	ret = &TailTask{
		BaseSchema: BaseSchema{
			BkBizID:     conf.BkBizID,
			BkCloudID:   conf.BkCloudID,
			ServerIP:    conf.ServerIP,
			ServerPort:  server_port,
			Domain:      conf.ClusterDomain,
			ClusterType: conf.ClusterType,
			Role:        conf.MetaRole,
		},
		ReportSaveDir: reportDir,
		wg:            &sync.WaitGroup{},
	}
	return
}

func (task *TailTask) redisConnect() {
	task.Password, task.Err = myredis.GetRedisPasswdFromConfFile(task.ServerPort)
	if task.Err != nil {
		return
	}
	addr := fmt.Sprintf("%s:%d", task.ServerIP, task.ServerPort)
	task.rediscli, task.Err = myredis.NewRedisClientWithTimeout(addr,
		task.Password, 0, consts.TendisTypeRedisInstance, 10*time.Second)
}

// RedisGetLogFiles get log files
func (task *TailTask) RedisGetLogFiles() {
	task.redisConnect()
	if task.Err != nil {
		return
	}
	defer task.rediscli.Close()
	var ret map[string]string
	ret, task.Err = task.rediscli.ConfigGet("logfile")
	if task.Err != nil {
		return
	}
	task.LogFiles = []string{ret["logfile"]}
	return
}

// TendisplusGetLogFiles get log files
func (task *TailTask) TendisplusGetLogFiles() {
	task.redisConnect()
	if task.Err != nil {
		return
	}
	defer task.rediscli.Close()
	var logDir string
	logDir, task.Err = task.rediscli.GetLogDir()
	if task.Err != nil {
		return
	}
	task.LogFiles = make([]string, 0, 2)
	task.LogFiles = append(task.LogFiles, filepath.Join(logDir, "tendisplus.WARNING"))
	task.LogFiles = append(task.LogFiles, filepath.Join(logDir, "tendisplus.ERROR"))
	return
}

// TwemproxyGetLogFiles get log files
func (task *TailTask) TwemproxyGetLogFiles() {
	var logFile string
	logFile, task.Err = util.GetTwemproxyLastLogFile(task.ServerPort)
	if task.Err != nil {
		return
	}
	if logFile == "" {
		task.Err = fmt.Errorf("TailTask TwemproxyGetLogFiles fail,logFile is empty,addr:%s,role:%s", task.Addr(), task.Role)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.LogFiles = []string{logFile}
	return
}

// PredixyGetLogFiles get log files
func (task *TailTask) PredixyGetLogFiles() {
	var logFile string
	logFile, task.Err = util.GetPredixyLastLogFile(task.ServerPort)
	if task.Err != nil {
		return
	}
	if logFile == "" {
		task.Err = fmt.Errorf("TailTask PredixyGetLogFiles fail,logFile is empty,addr:%s,role:%s", task.Addr(), task.Role)
		mylog.Logger.Error(task.Err.Error())
		return
	}
	task.LogFiles = []string{logFile}
	return
}

// GetLogFiles 获取每种db组件的日志文件
func (task *TailTask) GetLogFiles() {
	if task.Role == consts.MetaRolePredixy {
		task.PredixyGetLogFiles()
	} else if task.Role == consts.MetaRoleTwemproxy {
		task.TwemproxyGetLogFiles()
	} else if consts.IsRedisInstanceDbType(task.ClusterType) || consts.IsTendisSSDInstanceDbType(task.ClusterType) {
		task.RedisGetLogFiles()
	} else if consts.IsTendisplusInstanceDbType(task.ClusterType) {
		task.TendisplusGetLogFiles()
	}
	mylog.Logger.Info(fmt.Sprintf("TailTask %s %s found logfiles %+v", task.Addr(), task.Role, task.LogFiles))
}

// GetReporter 上报者
func (task *TailTask) GetReporter() {
	reportDir := filepath.Join(task.ReportSaveDir, "redis")
	util.MkDirsIfNotExists([]string{reportDir})
	util.LocalDirChownMysql(reportDir)
	task.ReportFile = fmt.Sprintf(consts.RedisServerLogRepoter,
		task.ServerPort,
		time.Now().Local().Format(consts.FilenameDayLayout))
	task.ReportFile = filepath.Join(reportDir, task.ReportFile)
	task.reporter, task.Err = report.NewFileReport(task.ReportFile)
}

// getNotIncludes 根据组件类型,获取不需要上报的日志行(包含这些字符串的日志行不上报)
func (task *TailTask) getNotIncludes() {
	var password string
	if task.Role == consts.MetaRolePredixy {
		task.NotIncludes = []string{"accept c", "remove c", "MissLog count"}
	} else if task.Role == consts.MetaRoleTwemproxy {
		password, task.Err = myredis.GetProxyPasswdFromConfFlie(task.ServerPort, task.Role)
		if task.Err != nil {
			return
		}
		task.NotIncludes = []string{password}
	} else if consts.IsRedisInstanceDbType(task.ClusterType) || consts.IsTendisSSDInstanceDbType(task.ClusterType) {
		task.NotIncludes = []string{}
	} else if consts.IsTendisplusInstanceDbType(task.ClusterType) {
		task.NotIncludes = []string{}
	}
}

// filterLogLine 如果日志行包含NotIncludes中的字符串,则不上报
func (task *TailTask) filterLogLine(line string) bool {
	if len(task.NotIncludes) == 0 {
		return true
	}
	for _, notInclude := range task.NotIncludes {
		if strings.Contains(line, notInclude) {
			return false
		}
	}
	return true
}

// BackgroundTailLog 后台运行tail groutine
func (task *TailTask) BackgroundTailLog() {
	for _, logFile := range task.LogFiles {
		if !util.FileExists(logFile) {
			continue
		}
		tailObj, err := tail.TailFile(logFile, tail.Config{
			ReOpen:    true,
			Follow:    true,
			Location:  &tail.SeekInfo{Offset: 0, Whence: io.SeekEnd},
			MustExist: true,
			Poll:      true,
			Logger:    mylog.GlobTailLogger,
		})
		if err != nil {
			err = fmt.Errorf("TailTask tail.TailFile %s fail,err:%v", logFile, err)
			mylog.Logger.Error(err.Error())
			task.Err = err
			return
		}
		task.TailObjs = append(task.TailObjs, tailObj)
	}
	// 每个日志文件一个goroutine,实时上报每个文件新增内容
	for _, tmpObj := range task.TailObjs {
		tailObj := tmpObj
		task.wg.Add(1)
		go func() {
			defer task.wg.Done()
			recordItem := LogRecordItem{}
			recordItem.BaseSchema = task.BaseSchema
			recordItem.LogFile = tailObj.Filename
			recordItem.TimeZone, _ = time.Now().Zone()
			mylog.Logger.Info(fmt.Sprintf("TailTask %s start tail log file:%s", task.Addr(), tailObj.Filename))
			for line := range tailObj.Lines {
				if line.Err != nil {
					continue
				}
				if line.Text == "" {
					continue
				}
				if !task.filterLogLine(line.Text) {
					continue
				}
				recordItem.CreateTime = line.Time.Local().Format(time.RFC3339)
				recordItem.Data = line.Text
				tmpBytes, _ := json.Marshal(recordItem)
				task.reporter.AddRecord(string(tmpBytes)+"\n", true)
			}
			mylog.Logger.Info(fmt.Sprintf("TailTask %s stop tail log file:%s", task.Addr(), tailObj.Filename))
		}()
	}
}

// StopTailLog 终止所有 tail goroutine并用 cleanup()清理资源
func (task *TailTask) StopTailLog() {
	mylog.Logger.Info(fmt.Sprintf("TailTask %s stop all tail goroutines", task.Addr()))
	for _, tailObj := range task.TailObjs {
		tailObj.Stop()
	}
	if task.done != nil {
		close(task.done)
	}
	task.wg.Wait()
	mylog.Logger.Info(fmt.Sprintf("TailTask %s cleanup all tail handlers", task.Addr()))
	for _, tailObj := range task.TailObjs {
		tailObj.Cleanup()
	}
	if task.reporter != nil {
		task.reporter.Close()
	}
	task.TailObjs = []*tail.Tail{}
}

// RunTailLog TODO
func (task *TailTask) RunTailLog() {
	task.Err = nil
	task.GetLogFiles()
	if task.Err != nil {
		return
	}
	task.GetReporter()
	if task.Err != nil {
		return
	}
	task.getNotIncludes()
	if task.Err != nil {
		return
	}
	task.BackgroundTailLog()
	if task.Err != nil {
		return
	}
	if task.Role == consts.MetaRoleTwemproxy && len(task.LogFiles) > 0 {
		task.RestartTailWhenTwemproxyNewLogfile()
	}
}

// RestartTailWhenTwemproxyNewLogfile 当twemproxy日志文件目录生成新日志文件时,重启tail
func (task *TailTask) RestartTailWhenTwemproxyNewLogfile() {
	task.done = make(chan struct{})
	task.wg.Add(1)
	go func() {
		foundNewFile := false
		defer func() {
			// 为何要在没有新 logFile 文件生成时,也要调用 wg.Done() ?
			// 因为在有新logFile文件生成时,foundNewFile=true,会在下面的for 循环之后调用 wg.Done()
			if !foundNewFile {
				task.wg.Done()
			}
		}()
		// logFile 示例 /data/twemproxy-0.2.4/50007/log/twemproxy.50007.log.20211018213421
		logFile := task.LogFiles[0]
		logDir := filepath.Dir(logFile)
		logFileName := filepath.Base(logFile)
		// logBaseName 只保留 twemproxy.50007.log,去掉后面的 .\d+ 部分
		logBaseName := strings.TrimSuffix(logFileName, filepath.Ext(logFileName))

		var watcher *fsnotify.Watcher
		watcher, task.Err = fsnotify.NewWatcher()
		if task.Err != nil {
			task.Err = fmt.Errorf("TailTask fsnotify.NewWatcher fail,err:%v", task.Err)
			mylog.Logger.Error(task.Err.Error())
			return
		}
		defer watcher.Close()
		task.Err = watcher.Add(logDir)
		if task.Err != nil {
			task.Err = fmt.Errorf("TailTask watcher.Add fail,dir:%s,err:%v", logDir, task.Err)
			mylog.Logger.Error(task.Err.Error())
			return
		}
		mylog.Logger.Info(fmt.Sprintf("TailTask %s start watch (fsnotify.Watcher) twemproxy log dir:%s", task.Addr(), logDir))

		for !foundNewFile {
			select {
			case event, ok := <-watcher.Events:
				if !ok {
					return
				}
				if event.Op&fsnotify.Create == fsnotify.Create && strings.Contains(event.Name, logBaseName) {
					mylog.Logger.Info(fmt.Sprintf("TailTask %s twemproxy log file %s created,restart tail", task.Addr(), event.Name))
					foundNewFile = true
					break
				}
			case err, ok := <-watcher.Errors:
				if !ok {
					return
				}
				mylog.Logger.Error(fmt.Sprintf("TailTask %s fsnotify error:%v", task.Addr(), err))
			case <-task.done:
				mylog.Logger.Info(fmt.Sprintf("TailTask task.done closed, %s stop watch (fsnotify.Watcher) twemproxy log dir:%s",
					task.Addr(), logDir))
				return
			}
		}
		if foundNewFile {
			// 这里必须调用 wg.Done(),否则 task.StopTailLog()中, task.wg.wait() 会一直等待
			task.wg.Done()
			task.StopTailLog()
			task.RunTailLog()
		}
	}()
}
