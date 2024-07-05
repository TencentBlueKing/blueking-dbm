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
	task.baseTask, err = newBaseTask(conf, serverConf)
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
	// twemproxy update 失败,也需要尝试重启twemproxy
	task.UpdateConfFileHashTag()
	task.RestartWhenConnFail()
	if task.Err != nil {
		return
	}
	return
}

// UpdateConfFileHashTag 更新twemproxy配置文件中的hash_tag: {} 为 hash_tag: '{}'
func (task *TwemproxyMonitorTask) UpdateConfFileHashTag() {
	var confFile string
	var proxyAddr string
	var msg string
	for _, proxyPort := range task.ServerConf.ServerPorts {
		proxyAddr = fmt.Sprintf("%s:%d", task.ServerConf.ServerIP, proxyPort)
		task.eventSender.SetInstance(proxyAddr)
		confFile, task.Err = myredis.GetTwemproxyLocalConfFile(proxyPort)
		if task.Err != nil {
			continue
		}
		confFile = strings.TrimSpace(confFile)
		if confFile == "" {
			msg = fmt.Sprintf("twemproxy(%s:%d) config file not found", task.ServerConf.ServerIP, proxyPort)
			mylog.Logger.Warn(msg)
			continue
		}
		if !util.FileExists(confFile) {
			msg = fmt.Sprintf("twemproxy(%s:%d) config file(%s) not exists",
				task.ServerConf.ServerIP, proxyPort, confFile)
			mylog.Logger.Warn(msg)
			continue
		}

		cmd := fmt.Sprintf(`
ret=$(grep "hash_tag: {}" %s || { true; })
if [[ -n "$ret" ]]
then
	sed -i -e "s/hash_tag: {}/hash_tag: '{}'/g" %s
fi`, confFile, confFile)
		_, task.Err = util.RunBashCmd(cmd, "", nil, 10*time.Second)
		if task.Err != nil {
			continue
		}
	}
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
			task.getPassword(proxyPort)
			if task.Err != nil {
				msg = fmt.Sprintf("twemproxy(%s) port in use, but connect failed,err:%s", proxyAddr, task.Err)
				task.eventSender.SendWarning(consts.EventTwemproxyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
				continue
			}
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
		task.getPassword(proxyPort)
		if task.Err != nil {
			msg = fmt.Sprintf("twemproxy(%s) restart but get password failed,err: %s", proxyAddr, task.Err)
			task.eventSender.SendWarning(consts.EventTwemproxyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			continue
		}
		task.proxyCli, task.Err = myredis.NewRedisClientWithTimeout(proxyAddr, task.Password, 0,
			consts.TendisTypeRedisInstance, 5*time.Second)
		if task.Err != nil {
			// twemproxy 重启失败
			msg = fmt.Sprintf("twemproxy(%s) restart but still connect fail", proxyAddr)
			mylog.Logger.Info(msg)
			task.eventSender.SendWarning(consts.EventTwemproxyLogin, msg, consts.WarnLevelError, task.ServerConf.ServerIP)
			return
		}
		msg = fmt.Sprintf("twemproxy(%s) restart and connect success", proxyAddr)
		mylog.Logger.Info(msg)
		task.eventSender.SendWarning(consts.EventTwemproxyRestart, msg, consts.WarnLevelWarning, task.ServerConf.ServerIP)
	}
}
