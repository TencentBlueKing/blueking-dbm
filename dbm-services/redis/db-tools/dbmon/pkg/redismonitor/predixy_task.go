package redismonitor

import (
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbmon/config"
	"dbm-services/redis/db-tools/dbmon/models/myredis"
	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"dbm-services/redis/db-tools/dbmon/util"
)

// PredixyMonitorTask Predixy monitor task
type PredixyMonitorTask struct {
	baseTask
	proxyCli *myredis.RedisClient `json:"-"`
	Err      error                `json:"-"`
}

// NewPredixyMonitorTask new
func NewPredixyMonitorTask(conf *config.Configuration, serverConf config.ConfServerItem,
	password string) (task *PredixyMonitorTask, err error) {
	task = &PredixyMonitorTask{}
	task.baseTask, err = newBaseTask(conf, serverConf, password)
	if err != nil {
		return
	}
	return
}

// RunMonitor run
func (task *PredixyMonitorTask) RunMonitor() {
	defer func() {
		if task.proxyCli != nil {
			task.proxyCli.Close()
		}
	}()

	task.RestartWhenConnFail()
	if task.Err != nil {
		return
	}
	return
}

// RestartWhenConnFail 当连接失败时重启Predixy
func (task *PredixyMonitorTask) RestartWhenConnFail() {
	var isPortInUse bool
	var msg string
	var proxyAddr string
	for _, proxyPort := range task.ServerConf.ServerPorts {
		task.eventSender.SetInstance(task.ServerConf.ServerIP + ":" + strconv.Itoa(proxyPort))
		proxyAddr = fmt.Sprintf("%s:%d", task.ServerConf.ServerIP, proxyPort)
		isPortInUse, _ = util.CheckPortIsInUse(task.ServerConf.ServerIP, strconv.Itoa(proxyPort))
		if isPortInUse {
			task.proxyCli, task.Err = myredis.NewRedisClientWithTimeout(proxyAddr, task.Password, 0,
				consts.TendisTypeRedisInstance, 5*time.Second)
			if task.Err == nil {
				// predixy 正常运行中
				mylog.Logger.Info(fmt.Sprintf("predixy(%s) check alive ok", proxyAddr))
				continue
			}
		}
		startScript := filepath.Join(consts.UsrLocal, "predixy", "bin", "start_predixy.sh")
		if !util.FileExists(startScript) {
			task.Err = fmt.Errorf("predixy(%s) connect fail,%s not exists??", proxyAddr, startScript)
			mylog.Logger.Error(task.Err.Error())
			task.eventSender.SendWarning(consts.EventPredixyLogin, task.Err.Error(),
				consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		startCmd := []string{startScript, strconv.Itoa(proxyPort)}
		mylog.Logger.Info(strings.Join(startCmd, " "))
		_, task.Err = util.RunLocalCmd(startCmd[0], startCmd[1:], "", nil, 10*time.Second)
		if task.Err != nil {
			msg = fmt.Sprintf("predixy(%s) connect fail,restart fail", task.proxyCli.Addr)
			mylog.Logger.Error(msg)
			task.eventSender.SendWarning(consts.EventPredixyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		task.proxyCli, task.Err = myredis.NewRedisClientWithTimeout(proxyAddr, task.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if task.Err != nil {
			// Predixy 重启失败
			msg = fmt.Sprintf("predixy(%s) restart but still connect fail", proxyAddr)
			mylog.Logger.Info(msg)
			task.eventSender.SendWarning(consts.EventPredixyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		msg = fmt.Sprintf("predixy(%s) restart and connect success", proxyAddr)
		mylog.Logger.Info(msg)
		task.eventSender.SendWarning(consts.EventPredixyRestart, msg, consts.WarnLevelWarning, task.ServerConf.ServerIP)
	}
}
