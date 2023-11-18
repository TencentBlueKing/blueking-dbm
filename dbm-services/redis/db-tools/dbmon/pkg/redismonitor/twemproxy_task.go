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

// TwemproxyMonitorTask twemproxy monitor task
type TwemproxyMonitorTask struct {
	baseTask
	proxyCli *myredis.RedisClient `json:"-"`
	Err      error                `json:"-"`
}

// NewTwemproxyMonitorTask new
func NewTwemproxyMonitorTask(conf *config.Configuration, serverConf config.ConfServerItem,
	password string) (task *TwemproxyMonitorTask, err error) {
	task = &TwemproxyMonitorTask{}
	task.baseTask, err = newBaseTask(conf, serverConf, password)
	if err != nil {
		return
	}
	return
}

// RunMonitor run
func (task *TwemproxyMonitorTask) RunMonitor() {
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

// RestartWhenConnFail 当连接失败时重启twemproxy
func (task *TwemproxyMonitorTask) RestartWhenConnFail() {
	var isPortInUse bool
	var msg string
	var proxyAddr string
	for _, proxyPort := range task.ServerConf.ServerPorts {
		proxyAddr = fmt.Sprintf("%s:%d", task.ServerConf.ServerIP, proxyPort)
		task.eventSender.SetInstance(proxyAddr)
		isPortInUse, _ = util.CheckPortIsInUse(task.ServerConf.ServerIP, strconv.Itoa(proxyPort))
		if isPortInUse {
			task.proxyCli, task.Err = myredis.NewRedisClientWithTimeout(proxyAddr, task.Password, 0,
				consts.TendisTypeRedisInstance, 5*time.Second)
			if task.Err == nil {
				// twemproxy 正常运行中
				mylog.Logger.Info(fmt.Sprintf("twemproxy(%s) check alive ok", proxyAddr))
				return
			}
		}
		startScript := filepath.Join(consts.UsrLocal, "twemproxy", "bin", "start_nutcracker.sh")
		if !util.FileExists(startScript) {
			task.Err = fmt.Errorf("twemproxy(%s) connect fail,%s not exists??", proxyAddr, startScript)
			mylog.Logger.Error(task.Err.Error())
			task.eventSender.SendWarning(consts.EventTwemproxyLogin, task.Err.Error(), consts.WarnLevelError,
				task.ServerConf.ServerIP)
			return
		}
		startCmd := []string{startScript, strconv.Itoa(proxyPort)}
		mylog.Logger.Info(strings.Join(startCmd, " "))
		_, task.Err = util.RunLocalCmd(startCmd[0], startCmd[1:], "", nil, 10*time.Second)
		if task.Err != nil {
			msg = fmt.Sprintf("twemproxy(%s) connect fail,restart fail", task.proxyCli.Addr)
			task.eventSender.SendWarning(consts.EventTwemproxyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		task.proxyCli, task.Err = myredis.NewRedisClientWithTimeout(proxyAddr, task.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if task.Err != nil {
			// twemproxy 重启失败
			msg = fmt.Sprintf("twemproxy(%s) restart but still connect fail", proxyAddr)
			mylog.Logger.Info(msg)
			task.eventSender.SendWarning(consts.EventTwemproxyRestart, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		msg = fmt.Sprintf("twemproxy(%s) restart and connect success", proxyAddr)
		mylog.Logger.Info(msg)
		task.eventSender.SendWarning(consts.EventTwemproxyRestart, msg, consts.WarnLevelWarning, task.ServerConf.ServerIP)
	}
}
