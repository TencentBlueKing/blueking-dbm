package atommongodb

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/common"
	"dbm-services/mongo/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongo/db-tools/dbactuator/pkg/util"
	"dbm-services/mongo/db-tools/dbmon/config"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/spf13/viper"

	"github.com/go-playground/validator/v10"

	"github.com/pkg/errors"
)

// installDbmon
// - 生成配置文件
// - 更新dbtools
// - 更新bk-dbmon
// - 启动服务(同时添加到开机启动)

// installDbmonParams 备份任务参数，由前端传入
type installDbmonParams struct {
	BkDbmonPkg    common.MediaPkg            `json:"bk_dbmon_pkg" validate:"required"` // bk-dbmon安装包
	DbToolsPkg    common.DbToolsMediaPkg     `json:"dbtools_pkg" validate:"required"`  // dbtools安装包
	ToolKitPkg    common.DbToolsMediaPkg     `json:"toolkit_pkg" validate:"required"`  // dbtools安装包
	Action        string                     `json:"action"  validate:"required"`
	ReportSaveDir string                     `json:"report_save_dir"  validate:"required"`
	ReportLeftDay int                        `json:"report_left_day"  validate:"required"`
	HttpAddress   string                     `json:"http_address"  validate:"required"`
	BkMonitorBeat config.BkMonitorBeatConfig `json:"bkmonitorbeat"  validate:"required"`
	Servers       []config.ConfServerItem    `json:"servers"  validate:"required"`
}

type installDbmonJob struct {
	BaseJob           // BaseJob 实现了jobruntime.JobRunner所需要的部分接口.
	params            *installDbmonParams
	updateDbmonFlag   bool // 是否已更新过dbmon
	configChangedFlag bool // 配置文件是否已更新
}

func (job *installDbmonJob) Param() string {
	o, _ := json.MarshalIndent(installDbmonParams{}, "", "\t")
	return string(o)
}

// NewInstallDbmonJob 实例化结构体
func NewInstallDbmonJob() jobruntime.JobRunner {
	return &installDbmonJob{}
}

// Name 获取原子任务的名字
func (job *installDbmonJob) Name() string {
	return "install_dbmon"
}

// Run 运行原子任务
func (job *installDbmonJob) Run() error {
	// 生成配置文件 updateDbTool updateDbmon startDbmon
	return job.runSteps([]stepFunc{
		{"updateConfigFile", job.updateConfigFile},
		{"updateDbTool", job.updateDbTool},
		{"updateToolKit", job.updateToolKit},
		{"updateDbmon", job.updateDbmon},
		{"startDbmon", job.startDbmon},
	})
}

// Init 初始化
func (job *installDbmonJob) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	job.runtime = runtime
	if checkIsRootUser() {
		return errors.New("This job cannot be executed as root user")
	}
	if err := json.Unmarshal([]byte(job.runtime.PayloadDecoded), &job.params); err != nil {
		return errors.Wrap(err, "payload json.Unmarshal failed")

	}
	if err := job.checkParams(); err != nil {
		return errors.Wrap(err, "checkParams")
	}
	return nil
}

// checkParams 校验参数
func (job *installDbmonJob) checkParams() error {
	// 参数有效性检查
	validate := validator.New()
	err := validate.Struct(job.params)
	if err == nil {
		return nil
	}

	var invalidValidationError *validator.InvalidValidationError
	if errors.As(err, &invalidValidationError) {
		job.runtime.Logger.Error("params validate failed,err:%v,params:%+v", err, job.params)
		return err
	}
	for _, e := range err.(validator.ValidationErrors) {
		job.runtime.Logger.Error("params validate failed, err:%v,params:%+v", e, job.params)
		return e
	}

	return nil
}

func loadConfigFile(configFile string) (*config.Configuration, error) {
	// 如果文件存在，对比文件内容，如果不一样，就更新文件.
	if !util.FileExists(configFile) {
		return nil, nil
	}

	conf := config.Configuration{
		LoadTime: time.Now().Format(time.RFC3339),
	}
	v := viper.New()
	v.SetConfigFile(configFile)
	v.SetConfigType("yaml")
	if err := v.ReadInConfig(); err != nil {
		return nil, errors.Wrap(err, "viper.ReadInConfig")
	}
	err := v.Unmarshal(&conf)
	return &conf, err
}

func compareServers(old, new []config.ConfServerItem) bool {
	if len(old) != len(new) {
		return false
	}
	sort.SliceStable(old, func(i, j int) bool {
		return old[i].Port < old[j].Port
	})
	sort.SliceStable(new, func(i, j int) bool {
		return new[i].Port < new[j].Port
	})
	for i, v := range old {
		if !reflect.DeepEqual(v, new[i]) {
			return false
		}
	}
	return true
}

func (job *installDbmonJob) updateConfigFile() error {
	// consts.BkDbmonPath
	configFile := consts.BkDbmonConfFile
	util.MkDirsIfNotExists([]string{path.Dir(configFile)})
	var conf config.Configuration
	conf.ReportSaveDir = job.params.ReportSaveDir
	conf.ReportLeftDay = job.params.ReportLeftDay
	conf.HttpAddress = job.params.HttpAddress
	conf.BkMonitorBeat = job.params.BkMonitorBeat
	conf.Servers = job.params.Servers

	// 如果文件存在，对比文件内容，如果不一样，就更新文件.
	oldConf, err := loadConfigFile(configFile)
	if err != nil {
		job.runtime.Logger.Warn("loadConfigFile %s failed, err:%v", configFile, err)
	}

	if oldConf != nil {
		if oldConf.ReportSaveDir == conf.ReportSaveDir &&
			oldConf.ReportLeftDay == conf.ReportLeftDay &&
			oldConf.HttpAddress == conf.HttpAddress &&
			oldConf.BkMonitorBeat == conf.BkMonitorBeat &&
			compareServers(oldConf.Servers, conf.Servers) {
			job.runtime.Logger.Info("config file %s has not been changed", configFile)
			return nil
		}
	}

	for i := 5; i >= 0; i-- {
		dstFile := fmt.Sprintf("%s.%d.bak", configFile, i)
		srcFile := fmt.Sprintf("%s.%d.bak", configFile, i-1)
		if i == 0 {
			dstFile = fmt.Sprintf("%s.%d.bak", configFile, i)
			srcFile = configFile
		}
		if util.FileExists(srcFile) {
			err = cpfile(srcFile, dstFile)
			if err != nil {
				job.runtime.Logger.Warn("cpfile %s to %s failed, err:%v", srcFile, dstFile, err)
			} else {
				job.runtime.Logger.Info("cpfile %s to %s success", srcFile, dstFile)
			}
		}
	}

	if err := config.WriteConfig(configFile, &conf); err != nil {
		return errors.Wrap(err, "WriteConfig")
	}
	job.configChangedFlag = true
	return nil
}

// todo 改为常量
func (job *installDbmonJob) updateDbTool() error {
	fileName := path.Base(job.params.DbToolsPkg.Pkg)
	prevFile := path.Join(consts.PackageCachePath, fileName)
	newFile := path.Join(consts.PackageSavePath, fileName)
	dstDir := "/home/mysql/dbtools/mg/"
	util.MkDirsIfNotExists([]string{dstDir})
	skipped, err := untarMedia(prevFile, newFile, dstDir)
	if err != nil {
		return errors.Wrap(err, "updateDbTool")
	}
	if skipped {
		job.runtime.Logger.Info(
			"updateDbTool %s to %s skipped. Because the MD5 value of the file has not changed.",
			newFile, dstDir)
		return nil
	}
	job.runtime.Logger.Info("updateDbTool %s to %s done", newFile, dstDir)
	cpfile(newFile, prevFile) // 只在成功untar后才能cp
	return nil
}

// todo 改为常量
func (job *installDbmonJob) updateToolKit() error {
	fileName := path.Base(job.params.ToolKitPkg.Pkg)
	prevFile := path.Join(consts.PackageCachePath, fileName)
	newFile := path.Join(consts.PackageSavePath, fileName)
	dstDir := "/home/mysql/dbtools/mg/"
	util.MkDirsIfNotExists([]string{dstDir})
	skipped, err := untarMedia(prevFile, newFile, dstDir)
	if err != nil {
		return errors.Wrap(err, "updateDbTool")
	}
	if skipped {
		job.runtime.Logger.Info(
			"updateDbTool %s to %s skipped. Because the MD5 value of the file has not changed.",
			newFile, dstDir)
		return nil
	}
	job.runtime.Logger.Info("updateDbTool %s to %s done", newFile, dstDir)
	cpfile(newFile, prevFile) // 只在成功untar后才能cp
	return nil
}

func (job *installDbmonJob) updateDbmon() error {
	fileName := path.Base(job.params.BkDbmonPkg.Pkg)
	prevFile := path.Join(consts.PackageCachePath, fileName)
	newFile := path.Join(consts.PackageSavePath, fileName)
	dstDir := "/home/mysql/"
	util.MkDirsIfNotExists([]string{dstDir})
	skiped, err := untarMedia(prevFile, newFile, dstDir)
	if err != nil {
		return errors.Wrap(err, "updateDbmon")
	}
	if skiped {
		job.runtime.Logger.Info(
			"updateDbmon %s to %s skipped. Because the MD5 value of the file has not changed.", newFile, dstDir)
		return nil
	}
	job.runtime.Logger.Info("updateDbmon %s to %s done", newFile, dstDir)
	job.updateDbmonFlag = true
	cpfile(newFile, prevFile) // 只在成功untar后才能cp
	return nil
}

// startDbmon 启动dbmon.
func (job *installDbmonJob) startDbmon() error {
	pid, err := dbmonIsRunning(consts.BkDbmonBin)
	if err != nil {
		return errors.Wrap(err, "dbmonIsRunning")
	}
	isRunning := pid > 0
	job.updateDbmonFlag = true // always restart bk-dbmon

	if isRunning {
		job.runtime.Logger.Info("bk-dbmon is running, and md5 is changed. no need to restart. ")
		if err := exec.Command("kill", "-9", strconv.Itoa(pid)).Run(); err != nil {
			return errors.Wrap(err, "kill -9")
		} else {
			job.runtime.Logger.Info("kill -9 %d (bk-dbmon) success", pid)
		}
		// todo 允许只更新配置文件 但不重启bk-dbmon
	} else {
		job.runtime.Logger.Info("bk-dbmon is not running")
	}

	pid, err = startDbmon(consts.BkDbmonBin, consts.BkDbmonConfFile, "output.log")
	if err != nil || pid <= 0 {
		return errors.Errorf("start dbmon failed, err:%v, pid:%d", err, pid)
	}

	job.runtime.Logger.Info("start dbmon success, pid:%d", pid)
	return nil
}

// untarMedia 更新dbtools和dbmon文件包的 逻辑
// 制品传到 /data/install/mongo-dbtools.tar.gz
// 上一个制品在 /data/dbbak/mongo-dbtools.tar.gz
// 如果和上一个制品不一样，就执行更新流程
func untarMedia(prevFile, newFile, dstDir string) (skipped bool, err error) {
	if !util.FileExists(newFile) {
		err = errors.Errorf("newFile %s not exists", newFile)
		return
	}

	// 如果文件md5一样，就不用更新了
	if fileMd5Eq(prevFile, newFile) {
		return true, nil
	}
	skipped = false
	if !util.DirExists(dstDir) {
		err = errors.Errorf("dstDir %s not exists", dstDir)
		return
	}

	var o *mycmd.ExecResult
	if strings.HasSuffix(newFile, ".tar.gz") {
		tarCmd := mycmd.New("tar", "-xzf", newFile, "-C", dstDir)
		o, err = tarCmd.Run2(time.Hour)
		if err != nil {
			err = errors.Errorf("untar failed cmd:%s, err:%v", o.Cmdline, err)
			return
		}
	} else {
		cpCmd := mycmd.New("cp", newFile, dstDir)
		o, err = cpCmd.Run2(time.Hour)
		if err != nil {
			err = errors.Errorf("untar failed cmd:%s, err:%v", o.Cmdline, err)
			return
		}
	}

	// 是否要将output打印出来呢？不了吧，太多了.
	return
}

func cpfile(src, dst string) error {
	if !util.FileExists(src) {
		return errors.New("src not exists")
	}
	cpCmd := mycmd.New("cp", src, dst)
	o, err := cpCmd.Run2(time.Minute * 10)
	if err != nil {
		return errors.Errorf("cmd:%s, err:%v", o.Cmdline, err)
	}
	return nil
}

func fileMd5Eq(file1, file2 string) bool {
	if !util.FileExists(file1) || !util.FileExists(file2) {
		return false
	}
	v1, _ := util.GetFileMd5(file1)
	v2, _ := util.GetFileMd5(file2)
	if v1 == "" || v2 == "" {
		return false
	}
	return v1 == v2
}

func getPIDByPort(port string) (string, error) {
	cmd := exec.Command("lsof", "-i", ":"+port, "-t", "-sTCP:LISTEN")
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}

	re := regexp.MustCompile(`\d+`)
	pid := re.FindString(string(output))

	return pid, nil
}

func getExeNameByPID(pid string) (string, error) {
	exePath := filepath.Join("/proc", pid, "exe")
	exeName, err := os.Readlink(exePath)
	if err != nil {
		return "", err
	}

	return exeName, nil
}

// check dbmon is running
func dbmonIsRunning(comm string) (pid int, err error) {
	comm = path.Base(comm)
	process, err := util.ListProcess()
	if err != nil {
		return 0, err
	}

	for _, p := range process {
		if p.Comm == comm {
			return p.Pid, nil
		}
	}
	return 0, nil
}

func startDbmon(dbmonBin, configFilePath, outputFileName string) (pid int, err error) {
	if !util.FileExists(dbmonBin) {
		err = errors.New("dbmonBin not exists")

	}
	if err = os.Chdir(path.Dir(dbmonBin)); err != nil {
		err = errors.Wrap(err, "os.Chdir")
		return
	}

	return mycmd.New(dbmonBin, "--config", path.Base(configFilePath)).RunBackground(outputFileName)
}
