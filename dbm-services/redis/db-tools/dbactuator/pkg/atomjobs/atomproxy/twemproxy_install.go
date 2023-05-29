package atomproxy

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
	"github.com/google/go-cmp/cmp"
	"github.com/pkg/errors"
)

/*
	TwemproxyInstall 原子任务
	检查参数
	检查环境
	  端口未被监听
	解压介质
	创建目录
    生成配置
      - 如果配置已经存在且相同，可以通过.
    拉起进程
      - 如果已经拉起，可以通过.

	binDir 二进制安装后的目录
	datadir  数据目录
*/

//

// twemproxyPortMin twemproxy min port
const twemproxyPortMin = 50000

// twemproxyPortMax twemproxy max port
const twemproxyPortMax = 59999

// twemproxyPrefix prefix
const twemproxyPrefix = "twemproxy"

// defaultFileMode file mode
const defaultFileMode = 0755 // 默认创建的文件Mode

// twemproxyDir twemproxy ，在gcs上是twemproxy-0.2.4. 为了不改拉起脚本，继续用这个.
const twemproxyDir = "twemproxy-0.2.4"

// const AdminPortIncr = 1000 // 管理端口，是端口+1000

// TwemproxyInstallParams 安装参数
type TwemproxyInstallParams struct {
	common.MediaPkg
	// 	DataDirs      []string          `json:"data_dirs"` //  /data /data1
	IP            string                 `json:"ip" validate:"required"`
	Port          int                    `json:"port" validate:"required"` //  只支持1个端口
	Password      string                 `json:"password"`
	RedisPassword string                 `json:"redis_password" `
	DbType        string                 `json:"db_type" validate:"required"`
	Servers       []string               `json:"servers"`
	ConfConfigs   map[string]interface{} `json:"conf_configs"`
}

// twemproxyInstall install twemproxy 原子任务
type twemproxyInstall struct {
	runtime     *jobruntime.JobGenericRuntime
	RealDataDir string // /data/redis
	BinDir      string // /usr/local/redis
	// ConfTemplate string // 配置模版 twemproxy 配置比较简单，不需要模板，直接由TwemproxyConf生成配置文件
	ExecUser  string // 这里把User Group搞成变量，其实没必要，直接用mysql.mysql就行了
	ExecGroup string
	params    *TwemproxyInstallParams
	Ports     int
	Chroot    string // 不再支持Chroot了
}

// NewTwemproxyInstall new
func NewTwemproxyInstall() jobruntime.JobRunner {
	return &twemproxyInstall{
		ExecUser:  consts.MysqlAaccount,
		ExecGroup: consts.MysqlGroup,
	}
}

// GetUserGroup user group
func (ti *twemproxyInstall) GetUserGroup() string {
	return fmt.Sprintf("%s.%s", ti.ExecUser, ti.ExecGroup)
}

// Init 初始化 主要是检查参数
func (ti *twemproxyInstall) Init(m *jobruntime.JobGenericRuntime) error {
	ti.runtime = m
	if err := validatorParams(ti); err != nil {
		return errors.Wrap(err, "validatorParams")
	}

	if err := ti.checkParams(); err != nil {
		return errors.Wrap(err, "checkParams")
	}
	return nil
}

// Name 原子任务名
func (ti *twemproxyInstall) Name() string {
	return "twemproxy_install"
}

func validatorParams(ti *twemproxyInstall) error {
	err := json.Unmarshal([]byte(ti.runtime.PayloadDecoded), &ti.params)
	if err != nil {
		ti.runtime.Logger.Error(fmt.Sprintf("json.Unmarshal failed,err:%+v", err))
		return err
	}

	// 参数有效性检查，为了兼容部署和拉起2个阶段
	validate := validator.New()
	err = validate.Struct(ti.params)
	if err == nil {
		return err
	}

	if _, ok := err.(*validator.InvalidValidationError); ok {
		ti.runtime.Logger.Error("%s Init params validate failed,err:%v,params:%+v", ti.Name(),
			err, ti.params)
		return errors.Wrap(err, "validator")
	}

	// 如果有多个error，只返回第1个.
	for _, err := range err.(validator.ValidationErrors) {
		ti.runtime.Logger.Error("%s Init params validate failed,err:%v,params:%+v", ti.Name(),
			err, ti.params)
		return errors.Wrap(err, "validator")
	}
	return nil
}

// checkParams 检查参数
func (ti *twemproxyInstall) checkParams() (err error) {
	// 要求 ti.params.MediaPkg.Pkg 要以twemproxy开头
	if !strings.HasPrefix(ti.params.MediaPkg.Pkg, twemproxyPrefix) {
		err = errors.Errorf("require pkg has prefix %s. pkg:%s", twemproxyPrefix, ti.params.MediaPkg.Pkg)
		ti.runtime.Logger.Error(err.Error())
		return err
	}

	// install_twemproxy 只做安装，不生成配置文件和拉起进程。所以只需要一个端口参数，其它不需要
	if ti.params.Port < twemproxyPortMin || ti.params.Port > twemproxyPortMax {
		err = fmt.Errorf("checkParams. Port(%d) must in range [%d,%d,]", ti.params.Port, twemproxyPortMin, twemproxyPortMax)
		ti.runtime.Logger.Error(err.Error())
		return err
	}

	// todo 检查密码复杂度 长度大于4 就可以，更复杂的放在前端去搞
	// todo 检查ip 是否正确?

	// 检查Server合法性
	confObj := common.NewTwemproxyConf()
	if err = confObj.CheckServersValid(ti.params.Servers); err != nil {
		err = fmt.Errorf("checkParams. params [servers] error: %v", err)
		ti.runtime.Logger.Error(err.Error())
		return err
	}

	// Check HashTag
	if v, e := ti.params.ConfConfigs["hast_tag"]; e {
		hashTag, ok := v.(string)
		if !ok || !(hashTag == "" || hashTag == "{}") {
			err = fmt.Errorf("checkParams. params [hast_tag] is not valid")
			ti.runtime.Logger.Error(err.Error())
			return err
		}
	}

	return nil
}

// Run 执行
func (ti *twemproxyInstall) Run() (err error) {
	// 安装目录
	err = ti.getRealDataDir()
	if err != nil {
		return errors.Wrap(err, "getRealDataDir")
	}

	// 解压
	err = ti.untarMedia()
	if err != nil {
		return errors.Wrap(err, "untarMedia")
	}

	// 创建实例目录
	err = initInstanceDir(ti.RealDataDir, strconv.Itoa(ti.params.Port), ti.GetUserGroup())
	if err != nil {
		return errors.Wrap(err, "initInstanceDir")
	}
	ti.runtime.Logger.Info("initInstanceDir success. %s", path.Join(ti.RealDataDir, strconv.Itoa(ti.params.Port)))

	// 创建配置文件.
	err = ti.mkConfigFile(ti.params.Port)
	if err != nil {
		return errors.Wrap(err, "mkConfigFile")
	}

	// 创建Exporter的配置文件
	err = ti.mkExporterConfigFile()
	if err != nil {
		return errors.Wrap(err, "mkExporterConfigFile")
	}

	if err = chownDir(ti.RealDataDir, ti.GetUserGroup()); err != nil {
		return errors.Wrap(err, "chownInstanceDir")
	}

	if installed, _ := ti.isTwemproxyRunning(ti.params.Port); installed {
		ti.runtime.Logger.Info("startProcess success. port %d already running", ti.params.Port)
		return
	}

	err = ti.startProcess(ti.params.Port)
	if err != nil {
		return errors.Wrap(err, "startProcess")
	}
	ti.runtime.Logger.Info("startProcess success. port %d", ti.params.Port)
	return nil
}

// getPathWitChRoot Chroot是为了本地测试方便
func getPathWitChRoot(chroot string, elem ...string) string {
	if chroot == "" || chroot == "/" {
		return filepath.Join(elem...)
	}

	return filepath.Join(chroot, filepath.Join(elem...))
}

// doUnTar 将pkgAbsPath解压到dstPathParent,生成dstPath，并设置 owner
func doUnTar(pkgAbsPath, dstPathParent, dstPath, owner string) (err error) {
	tarCmd := fmt.Sprintf("tar -zxf %s -C %s", pkgAbsPath, dstPathParent)
	_, err = util.RunBashCmd(tarCmd, "", nil, 10*time.Second)
	if err != nil {
		return errors.Wrap(err, tarCmd)
	}
	return chownDir(dstPath, owner)
}

// addOsPath 把Path加到/etc/profile。这里/etc/profile也做了Chroot转义
func addOsPath(path, etcProfilePath string) error {
	addEtcProfile := fmt.Sprintf(`
if ! grep -i %s: %s; 
then 
echo "export PATH=%s:\$PATH" >> %s 
fi`, path, etcProfilePath, path, etcProfilePath)
	_, err := util.RunBashCmd(addEtcProfile, "", nil, 10*time.Second)
	return err
}

// fileIsExists 文件是否存在.
func fileIsExists(filePath string) (e bool, err error) {
	_, err = os.Stat(filePath)
	if err == nil {
		return true, nil
	}

	if os.IsNotExist(err) {
		return false, nil
	}

	return false, err
}

// untarMedia 解压安装包
func (ti *twemproxyInstall) untarMedia() (err error) {
	err = ti.params.MediaPkg.Check()
	if err != nil {
		ti.runtime.Logger.Error("UntarMedia failed,err:%v", err)
		return
	}
	pkgBaseName := ti.params.MediaPkg.GePkgBaseName()

	softLink := getPathWitChRoot(ti.Chroot, consts.UsrLocal, "twemproxy")
	twemproxyFullPath := getPathWitChRoot(ti.Chroot, consts.UsrLocal, pkgBaseName)

	exists, _ := fileIsExists(twemproxyFullPath)
	if exists {
		ti.runtime.Logger.Info("untarMedia. %s is exists, skip untar", twemproxyFullPath)
	} else {
		_ = doUnTar(ti.params.MediaPkg.GetAbsolutePath(),
			getPathWitChRoot(ti.Chroot, consts.UsrLocal), twemproxyFullPath, ti.GetUserGroup())
	}
	// 再测试一次，不存在就有问题了.
	if exists, _ := fileIsExists(twemproxyFullPath); !exists {
		err = fmt.Errorf("untarMedia failed. %s->%s", ti.params.MediaPkg.GetAbsolutePath(), twemproxyFullPath)
		ti.runtime.Logger.Error(err.Error())
		return
	}

	_, err = os.Stat(softLink)
	if err != nil && os.IsNotExist(err) {
		// 创建软链接 相当于 ln -s ti.BinDir softLink
		err = os.Symlink(twemproxyFullPath, softLink)
		if err != nil {
			err = fmt.Errorf("os.Symlink failed,err:%v,dir:%s,softLink:%s", err, twemproxyFullPath, softLink)
			ti.runtime.Logger.Error(err.Error())
			return
		}
		ti.runtime.Logger.Info("get binDir success. binDir:%s,softLink:%s", twemproxyFullPath, softLink)
	}

	realLink, err := filepath.EvalSymlinks(softLink)
	if err != nil {
		err = fmt.Errorf("filepath.EvalSymlinks failed,err:%v,softLink:%s", err, softLink)
		ti.runtime.Logger.Error(err.Error())
		return
	}

	baseName := filepath.Base(realLink)
	if pkgBaseName != baseName {
		err = fmt.Errorf("%s 指向 %s 而不是 %s", softLink, baseName, pkgBaseName)
		ti.runtime.Logger.DPanic(err.Error())
		return
	}

	ti.BinDir = filepath.Join(softLink, "bin")
	_ = addOsPath(ti.BinDir, getPathWitChRoot(ti.Chroot, "/etc/profile"))
	_ = chownDir(softLink, ti.GetUserGroup())
	ti.runtime.Logger.Info(fmt.Sprintf("binDir:%s", ti.BinDir))
	return nil
}

// myFindFirstMountPoint find first mountpoint in prefer order
func myFindFirstMountPoint(paths ...string) (string, error) {
	for _, filePath := range paths {
		if _, err := os.Stat(filePath); err != nil {
			if os.IsNotExist(err) {
				continue
			}
		}
		isMountPoint, err := util.IsMountPoint(filePath)
		if err != nil {
			return "", fmt.Errorf("check whether mountpoint failed, filePath: %s, err: %w", filePath, err)
		}
		if isMountPoint {
			return filePath, nil
		}
	}
	return "", nil
}

// getRealDataDir 确认redis Data Dir
func (ti *twemproxyInstall) getRealDataDir() error {
	data := consts.GetRedisDataDir()
	ti.RealDataDir = getPathWitChRoot(ti.Chroot, data, twemproxyDir)
	return nil
}

// mkDir 类似os.Mkdir，它有10秒超时
func mkDir(filePath string) error {
	_, err := util.RunBashCmd(fmt.Sprintf("mkdir -p %s", filePath), "", nil, 10*time.Second)
	return err
}

// chownDir 类似os.Chown，有10秒超时
func chownDir(filePath, userGroup string) error {
	_, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s %s", userGroup, filePath),
		"", nil,
		10*time.Second)

	return err
}

// initInstanceDir 初始化实例文件夹
// mkdir -p %DataDir%
// chown -R user.group  %DataDir%
func initInstanceDir(realDataDir, port, userGroup string) (err error) {
	instDir := filepath.Join(realDataDir, port)
	err = util.MkDirsIfNotExistsWithPerm([]string{instDir}, defaultFileMode)
	if err != nil {
		return err
	}

	return chownDir(realDataDir, userGroup)
}

// isTwemproxyRunning 检查已经安装
func (ti *twemproxyInstall) isTwemproxyRunning(port int) (installed bool, err error) {
	portIsUse, err := util.CheckPortIsInUse(ti.params.IP, strconv.Itoa(port))
	return portIsUse, err
}

// mkConfigFile 生成配置文件
func (ti *twemproxyInstall) mkConfigFile(port int) error {
	// /data/twemproxy-0.2.4/50010/nutcracker.50010.yml
	instConfigFileName := fmt.Sprintf("nutcracker.%d.yml", port)
	portStr := strconv.Itoa(port)
	instConfigFilePath := filepath.Join(ti.RealDataDir, portStr, instConfigFileName)

	// ti.params.ConfConfigs
	instConfig := common.NewTwemproxyConf()

	instConfig.NosqlProxy.Password = ti.params.Password
	instConfig.NosqlProxy.RedisPassword = ti.params.RedisPassword
	// 在Init 已经检查过了.
	newServers, _ := common.ReFormatTwemproxyConfServer(ti.params.Servers)
	instConfig.NosqlProxy.Servers = newServers
	instConfig.NosqlProxy.Listen = fmt.Sprintf("%s:%d", ti.params.IP, ti.params.Port)

	instConfig.NosqlProxy.SlowMs = 1000000 // 建议，经验值
	instConfig.NosqlProxy.Backlog = 512    // 建议，经验值
	// 固定参数
	instConfig.NosqlProxy.Redis = true              // 必须
	instConfig.NosqlProxy.Distribution = "modhash"  // 必须
	instConfig.NosqlProxy.Hash = "fnv1a_64"         // 必须
	instConfig.NosqlProxy.AutoEjectHosts = false    // 必须
	instConfig.NosqlProxy.ServerConnections = 1     // 必须，避免出现"后发先致"的问题
	instConfig.NosqlProxy.ServerFailureLimit = 3    // 建议，经验值
	instConfig.NosqlProxy.PreConnect = false        // 建议，经验值
	instConfig.NosqlProxy.ServerRetryTimeout = 2000 // 建议，经验值
	if v, e := ti.params.ConfConfigs["hash_tag"]; e {
		instConfig.NosqlProxy.HashTag, _ = v.(string)
	}

	exists, err := fileIsExists(instConfigFilePath)
	// 存在未知的错误
	if err != nil {
		return err
	}

	if exists {
		currInstConfig := common.NewTwemproxyConf()
		if err = currInstConfig.Load(instConfigFilePath); err != nil {
			return errors.Errorf("文件已存在，且读取失败, file:%s", instConfigFilePath)
		}
		if !cmp.Equal(currInstConfig, instConfig) {
			return errors.Errorf("文件已存在，内容不同, file:%s", instConfigFilePath)
		}
		ti.runtime.Logger.Info("文件已存在，但内容相同. file:%s", instConfigFilePath)
		return nil
	}

	err = instConfig.Save(instConfigFilePath, defaultFileMode)
	if err != nil {
		return errors.Errorf("写入文件失败, file:%s, err:%v", instConfigFilePath, err)
	}
	return nil
}

// mkExporterConfigFile TODO
// mkConfigFile 生成Exporter的配置文件
// 格式为 { "$ip:$port" : "password",
//
//	         "$ip:$port:stat" : "ip:$statPort",
//	}
func (ti *twemproxyInstall) mkExporterConfigFile() error {
	data := make(map[string]string)
	key := fmt.Sprintf("%s:%d", ti.params.IP, ti.params.Port)
	data[key] = ti.params.Password
	statKey := fmt.Sprintf("%s:%d:stat", ti.params.IP, ti.params.Port)
	data[statKey] = fmt.Sprintf("%s:%d", ti.params.IP, ti.params.Port+1000)
	return common.WriteExporterConfigFile(ti.params.Port, data)
}

func findLastLog(instDir string, port int) string {
	dir := path.Join(instDir, "log")
	prefix := fmt.Sprintf("twemproxy.%d.log.", port)
	files, err := ioutil.ReadDir(dir)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var modTime time.Time
	var name string
	for _, fi := range files {
		if !fi.Mode().IsRegular() {
			continue
		}
		if !strings.HasPrefix(fi.Name(), prefix) {
			continue
		}

		if fi.ModTime().Before(modTime) {
			continue
		}

		if fi.ModTime().After(modTime) {
			modTime = fi.ModTime()
			name = fi.Name()
		}
	}
	return path.Join(dir, name)
}

// startProcess 拉起实例
func (ti *twemproxyInstall) startProcess(port int) error {
	var installed bool
	var err error

	instDir := filepath.Join(ti.RealDataDir, strconv.Itoa(port))
	// log is twemproxy.$PORT.err
	instLogFile := filepath.Join(instDir, "log", fmt.Sprintf("twemproxy.%d.err", port))
	startScript := filepath.Join(ti.BinDir, "start_nutcracker.sh")

	installed, err = ti.isTwemproxyRunning(port)
	if err != nil {
		return err
	} else if installed {
		return nil
	}

	// https://unix.stackexchange.com/questions/327551/etc-profile-not-sourced-for-sudo-su
	// su - username -c "script.sh args..." 会load /etc/profile
	// su username  -c "script.sh args..." 不会load /etc/profile
	// twemproxy不需要再次 source/etc/profile

	startCmd := []string{"su", ti.ExecUser, "-c", fmt.Sprintf("%s %s", startScript, strconv.Itoa(port))}

	_, err = util.RunLocalCmd(startCmd[0], startCmd[1:], "",
		nil, 10*time.Second)

	if err != nil {
		return err
	}
	ti.runtime.Logger.Info(fmt.Sprintf("startProcess %s", startCmd))
	time.Sleep(2 * time.Second)

	installed, err = ti.isTwemproxyRunning(port)
	if installed {
		// 启动成功
		return nil
	} else if err != nil {
		return err
	}

	//  /data/twemproxy-0.2.4/50144/log/twemproxy.50144.err
	logData, err := util.RunBashCmd(fmt.Sprintf("tail -3 %s", instLogFile), "", nil, 10*time.Second)
	if err != nil {
		return err
	}
	// /data/twemproxy-0.2.4/50144/log/twemproxy.50144.log.$time
	var logData2 string
	lastLog := findLastLog(instDir, port)
	if lastLog != "" {
		logData2, _ = util.RunBashCmd(fmt.Sprintf("tail -4 %s", lastLog), "", nil, 10*time.Second)
	}

	err = fmt.Errorf("twemproxy(%s:%d) startup failed,errLog:%s,logData:%s", ti.params.IP, port, logData, logData2)
	ti.runtime.Logger.Error(err.Error())
	return err

}

// Retry times
func (ti *twemproxyInstall) Retry() uint {
	return 2
}

// Rollback rollback
func (ti *twemproxyInstall) Rollback() error {
	return nil
}
