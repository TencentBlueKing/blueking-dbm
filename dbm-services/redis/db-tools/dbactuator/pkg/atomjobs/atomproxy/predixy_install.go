package atomproxy

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/common"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
	"github.com/pkg/errors"
)

/*
1.安装前预检查
  获取主机名，内存，cpu信息
  检查IP地址

  获取信息 app ip  端口port  predixy版本  predixy密码 后端redis的密码 后端server数组ip:port

2.创建相关目录
/usr/local/predixy/bin/predixy /data/predixy/50004//predixy.conf
                               /data/predixy/50004/logs

2.获取安装包
predixy-1.0.5.tar.gz  放到/usr/local

3.解压安装包
安装目录为/usr/local
做软连接 ln -s /usr/local/predixy-1.0.5 predixy

4.获取predixy的配置文件并把后端信息写入配置文件


5.启动服务
 /usr/local/predixy/bin/start_predixy.sh $port
*/

// PredixyPortMin predixy最小端口
const PredixyPortMin = 50000

// PredixyPortMax predixy最大端口
const PredixyPortMax = 59999

// DefaultPerm 创建目录、文件的默认权限
const DefaultPerm = 0755

// PredixyConfParams predixy配置文件参数
type PredixyConfParams struct {
	common.MediaPkg `json:"mediapkg"`
	IP              string   `json:"ip" validate:"required"`
	Port            int      `json:"port" validate:"required"`
	PredixyPasswd   string   `json:"predixypasswd" validate:"required"`
	RedisPasswd     string   `json:"redispasswd" validate:"required"`
	Servers         []string `json:"servers" validate:"required"`
	DbConfig        struct {
		WorkerThreads      string `json:"workerthreads" validate:"required"`
		ClientTimeout      string `json:"clienttimeout"`
		RefreshInterval    string `json:"refreshinterval" validate:"required"`
		ServerFailureLimit string `json:"serverfailurelimit" validate:"required"`
		ServerRetryTimeout string `json:"serverretrytimeout" validate:"required"`
		KeepAlive          string `json:"keepalive"`
		ServerTimeout      string `json:"servertimeout"`
	} `json:"dbconfig" validate:"required"`
}

// PredixyInstall  predixy安装
type PredixyInstall struct {
	runtime         *jobruntime.JobGenericRuntime
	BinDir          string
	DataDir         string
	OsUser          string // predixy安装在哪个用户下
	OsGroup         string
	ConfParams      *PredixyConfParams
	ConfDir         string
	ConfFilePath    string
	ConfFileContent string
	LogDir          string
	InstallFilePath string
}

// NewPredixyInstall 实例化结构体
func NewPredixyInstall() jobruntime.JobRunner {
	return &PredixyInstall{}
}

// Init 初始化
func (p *PredixyInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	p.BinDir = consts.UsrLocal
	p.DataDir = consts.GetRedisDataDir()
	p.OsUser = consts.MysqlAaccount
	p.OsGroup = consts.MysqlGroup
	p.runtime = runtime
	p.runtime.Logger.Info("start to init")

	// 获取predixy配置文件参数
	if err := json.Unmarshal([]byte(p.runtime.PayloadDecoded), &p.ConfParams); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf(
			"%s:get parameters of predixy configer file fail by json.Unmarshal, error:%v", p.Name(), err))
		return fmt.Errorf(
			"%s:get parameters of predixy configer file fail by json.Unmarshal, error:%v", p.Name(), err)
	}
	// 获取各种文件路径
	p.ConfDir = fmt.Sprintf("%s/predixy/%d", p.DataDir, p.ConfParams.Port)
	p.ConfFilePath = fmt.Sprintf("%s/predixy.conf", p.ConfDir)
	p.LogDir = fmt.Sprintf("%s/logs", p.ConfDir)
	p.InstallFilePath = p.ConfParams.MediaPkg.GetAbsolutePath()
	p.getConfFileContent()
	p.runtime.Logger.Info("init successfully")
	// 校验参数
	if err := p.checkParams(); err != nil {
		return err
	}

	return nil
}

// getConfFileContent 获取配置文件内容
func (p *PredixyInstall) getConfFileContent() {
	p.runtime.Logger.Info("start to make config file content")
	// 配置文件
	conf := common.PredixConf
	// 修改配置文件
	bind := fmt.Sprintf("%s:%s", p.ConfParams.IP, strconv.Itoa(p.ConfParams.Port))
	log := fmt.Sprintf("%s/log", p.LogDir)
	var servers string
	for _, v := range p.ConfParams.Servers {
		servers += fmt.Sprintf("    + %s\n", v)
	}
	conf = strings.Replace(conf, "{{ip:port}}", bind, -1)
	conf = strings.Replace(conf, "{{predixy_password}}", p.ConfParams.PredixyPasswd, -1)
	conf = strings.Replace(conf, "{{log_path}}", log, -1)
	conf = strings.Replace(conf, "{{redis_password}}", p.ConfParams.RedisPasswd, -1)
	conf = strings.Replace(conf, "{{server:port}}", servers, -1)
	conf = strings.Replace(conf, "{{worker_threads}}", p.ConfParams.DbConfig.WorkerThreads, -1)
	conf = strings.Replace(conf, "{{server_timeout}}", p.ConfParams.DbConfig.ServerTimeout, -1)
	conf = strings.Replace(conf, "{{keep_alive}}", p.ConfParams.DbConfig.KeepAlive, -1)
	conf = strings.Replace(conf, "{{client_timeout}}", p.ConfParams.DbConfig.ClientTimeout, -1)
	conf = strings.Replace(conf, "{{refresh_interval}}",
		p.ConfParams.DbConfig.RefreshInterval, -1)
	conf = strings.Replace(conf, "{{server_failure_limit}}",
		p.ConfParams.DbConfig.ServerFailureLimit, -1)
	conf = strings.Replace(conf, "{{server_retry_timeout}}",
		p.ConfParams.DbConfig.ServerRetryTimeout, -1)
	p.ConfFileContent = conf
	p.runtime.Logger.Info("make config file content successfully")
}

// checkParams 校验参数
func (p *PredixyInstall) checkParams() error {
	p.runtime.Logger.Info("start to validate parameters")
	// 校验predixy配置文件
	validate := validator.New()
	if err := validate.Struct(p.ConfParams); err != nil {
		p.runtime.Logger.Error(
			fmt.Sprintf("%s:validate parameters of predixy configer file fail, error:%s", p.Name(), err))
		return fmt.Errorf("%s:validate parameters of predixy configer file fail, error:%s", p.Name(), err)
	}
	// 校验port是否合规
	if p.ConfParams.Port < PredixyPortMin || p.ConfParams.Port > PredixyPortMax {
		p.runtime.Logger.Error(fmt.Sprintf(
			"%s:validate parameters of predixy configer file fail, port is not within defalut range [%d,%d]",
			p.Name(), PredixyPortMin, PredixyPortMax))
		return errors.New(fmt.Sprintf(
			"%s:validate parameters of predixy configer file fail, port is not within defalut range [%d,%d]",
			p.Name(), PredixyPortMin, PredixyPortMax))
	}

	// 校验servers
	if len(p.ConfParams.Servers) < 2 {
		p.runtime.Logger.Error(fmt.Sprintf(
			"%s:validate parameters of predixy configer file fail, ser, the number of server is incorrect", p.Name()))
		return errors.New(fmt.Sprintf(
			"%s:validate parameters of predixy configer file fail, ser, the number of server is incorrect", p.Name()))
	}
	// 校验安装包是否存在，md5值是否一致
	if flag := util.FileExists(p.InstallFilePath); !flag {
		p.runtime.Logger.Error(fmt.Sprintf("%s:validate install file, %s is not existed", p.Name(), p.InstallFilePath))
		return errors.New(fmt.Sprintf("%s:validate install file, %s is not existed", p.Name(), p.InstallFilePath))
	}
	md5, _ := util.GetFileMd5(p.InstallFilePath)
	if p.ConfParams.MediaPkg.PkgMd5 != md5 {
		p.runtime.Logger.Error(fmt.Sprintf("%s:validate install file md5 fail, md5 is incorrect", p.Name()))
		return errors.New(fmt.Sprintf("%s:validate install file md5 fail, md5 is incorrect", p.Name()))
	}
	// 校验端口是否使用
	flag, _ := util.CheckPortIsInUse(p.ConfParams.IP, strconv.Itoa(p.ConfParams.Port))
	if flag {
		// 校验端口是否是predixy进程
		cmd := fmt.Sprintf("netstat -ntpl |grep %d | awk '{print $7}'", p.ConfParams.Port)
		result, _ := util.RunBashCmd(cmd, "", nil, 10*time.Second)
		if strings.Contains(result, "predixy") {
			// 检查配置文件是否一致
			// 读取已有配置文件与新生成的配置文件内容对比
			content, _ := ioutil.ReadFile(p.ConfFilePath)
			if strings.Compare(string(content), p.ConfFileContent) == 0 {
				p.runtime.Logger.Info("predixy port:%d has been installed", p.ConfParams.Port)
				os.Exit(0)
			}

		}
		p.runtime.Logger.Error(fmt.Sprintf("%s:validate parameters of predixy configer file fail, port:%s is used",
			p.Name(), strconv.Itoa(p.ConfParams.Port)))
		return fmt.Errorf("%s:validate parameters of predixy configer file fail, port:%d is used",
			p.Name(), p.ConfParams.Port)
	}
	p.runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 获取原子任务的名字
func (p *PredixyInstall) Name() string {
	return "predixy_install"
}

// Run 运行原子任务
func (p *PredixyInstall) Run() error {
	// 创建相关目录并给目录授权
	if err := p.mkdir(); err != nil {
		return err
	}
	// 解压安装包，创建软链接并给目录授权
	if err := p.unTarAndCreateSoftLink(); err != nil {
		return err
	}
	// 创建配置文件，并把配置文件参数进行替换
	if err := p.createConfFile(); err != nil {
		return err
	}
	// 创建Exporter的配置文件
	if err := p.mkExporterConfigFile(); err != nil {
		return errors.Wrap(err, "mkExporterConfigFile")
	}
	// 启动服务
	if err := p.startup(); err != nil {
		return err
	}

	return nil
}

// mkdir 创建相关目录并给目录授权
func (p *PredixyInstall) mkdir() error {
	p.runtime.Logger.Info("start to create directories")
	// 创建日志文件路径
	if err := util.MkDirsIfNotExistsWithPerm([]string{p.LogDir}, DefaultPerm); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:create directory fail, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:create directory fail, error:%s", p.Name(), err))
	}
	// 修改属主
	if _, err := util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s/predixy", p.OsUser, p.OsGroup, p.DataDir),
		"", nil,
		10*time.Second); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:chown directory fail, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:chown directory fail, error:%s", p.Name(), err))
	}
	p.runtime.Logger.Info("create directories successfully")
	return nil
}

// unTarAndCreateSoftLink 解压安装包，创建软链接并给目录授权
func (p *PredixyInstall) unTarAndCreateSoftLink() error {
	if !util.FileExists(fmt.Sprintf("%s/%s", p.BinDir, p.ConfParams.MediaPkg.GePkgBaseName())) {
		// 解压到/usr/local目录下
		p.runtime.Logger.Info("start to unTar install package")
		tarCmd := fmt.Sprintf("tar -zxf %s -C %s", p.InstallFilePath, p.BinDir)
		if _, err := util.RunBashCmd(tarCmd, "", nil, 10*time.Second); err != nil {
			p.runtime.Logger.Error(fmt.Sprintf("%s:untar install file  fail, error:%s", p.Name(), err))
			return errors.New(fmt.Sprintf("%s:untar install file  fail, error:%s", p.Name(), err))
		}
		p.runtime.Logger.Info("unTar install package successfully")
	}

	if !util.FileExists(fmt.Sprintf("%s/predixy", p.BinDir)) {
		// 创建软链接
		p.runtime.Logger.Info("start to create soft link of install package")
		baseName := p.ConfParams.MediaPkg.GePkgBaseName()
		softLink := fmt.Sprintf("ln -s %s/%s %s/predixy", p.BinDir, baseName, p.BinDir)
		if _, err := util.RunBashCmd(softLink, "", nil, 10*time.Second); err != nil {
			p.runtime.Logger.Error(fmt.Sprintf("%s:install file create softlink fail, error:%s", p.Name(), err))
			return errors.New(fmt.Sprintf("%s:install file create softlink fail, error:%s", p.Name(), err))
		}
		// 修改属主
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s.%s %s/predixy", p.OsUser, p.OsGroup, p.BinDir),
			"", nil,
			10*time.Second); err != nil {
			p.runtime.Logger.Error(fmt.Sprintf("%s:chown softlink directory fail, error:%s", p.Name(), err))
			return errors.New(fmt.Sprintf("%s:chown softlink directory fail, error:%s", p.Name(), err))
		}
		if _, err := util.RunBashCmd(
			fmt.Sprintf("chown -R %s.%s %s/%s", p.OsUser, p.OsGroup, p.BinDir, p.ConfParams.MediaPkg.GePkgBaseName()),
			"", nil,
			10*time.Second); err != nil {
			p.runtime.Logger.Error(fmt.Sprintf("%s:chown untar directory fail, error:%s", p.Name(), err))
			return errors.New(fmt.Sprintf("%s:chown untar directory fail, error:%s", p.Name(), err))
		}
		// 修改启动文件内容
		if _, err := util.RunBashCmd(
			fmt.Sprintf("sed -i \"s/\\/data/\\%s/g\" %s/predixy/bin/start_predixy.sh", p.DataDir, p.BinDir),
			"", nil,
			10*time.Second); err != nil {
			p.runtime.Logger.Error(fmt.Sprintf("%s:modfiy start_predixy.sh fail, error:%s", p.Name(), err))
			return errors.New(fmt.Sprintf("%s:modfiy start_predixy.sh fail, error:%s", p.Name(), err))
		}
		p.runtime.Logger.Info("create soft link of install package successfully")
	}
	return nil

}

// createConfFile 创建配置文件，并把配置文件参数进行替换
func (p *PredixyInstall) createConfFile() error {
	// 创建配置文件
	p.runtime.Logger.Info("start to create config file")
	file, err := os.OpenFile(p.ConfFilePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, DefaultPerm)
	if err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:create configer file fail, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:create configer file fail, error:%s", p.Name(), err))
	}
	defer file.Close()

	if _, err = file.WriteString(p.ConfFileContent); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:configer file write content fail, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:configer file write content  fail, error:%s", p.Name(), err))
	}
	// 修改配置文件属主
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", p.OsUser, p.OsGroup, p.ConfFilePath),
		"", nil,
		10*time.Second); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:chown configer file fail, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:chown configer file fail, error:%s", p.Name(), err))
	}
	p.runtime.Logger.Info("create config file successfully")
	return nil
}

// mkExporterConfigFile 生成Exporter的配置文件
// 格式为 { "ip:port" : "password" }
func (p *PredixyInstall) mkExporterConfigFile() error {
	data := make(map[string]string)
	key := fmt.Sprintf("%s:%d", p.ConfParams.IP, p.ConfParams.Port)
	data[key] = p.ConfParams.PredixyPasswd
	return common.WriteExporterConfigFile(p.ConfParams.Port, data)
}

// startup 启动服务
func (p *PredixyInstall) startup() error {
	// 启动服务
	p.runtime.Logger.Info("start to startup process")
	startCmd := fmt.Sprintf("su  %s -c \"%s/predixy/bin/start_predixy.sh %d\"", p.OsUser, p.BinDir,
		p.ConfParams.Port)
	p.runtime.Logger.Info("startup predixy, run %s", startCmd)
	if _, err := util.RunBashCmd(
		fmt.Sprintf("su %s -c \"%s/predixy/bin/start_predixy.sh %d\"", p.OsUser, p.BinDir, p.ConfParams.Port),
		"", nil,
		10*time.Second); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:startup predixy service, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:startup predixy service, error:%s", p.Name(), err))
	}
	// 申明predixy可执行文件路径，把路径写入/etc/profile
	etcProfilePath := "/etc/profile"
	addEtcProfile := fmt.Sprintf(`
if ! grep -i %s/predixy/bin: %s; 
then 
echo "export PATH=%s/predixy/bin:\$PATH" >> %s 
fi`, p.BinDir, etcProfilePath, p.BinDir, etcProfilePath)
	p.runtime.Logger.Info(addEtcProfile)
	if _, err := util.RunBashCmd(addEtcProfile, "", nil, 10*time.Second); err != nil {
		p.runtime.Logger.Error(fmt.Sprintf("%s:binary path add in /etc/profile, error:%s", p.Name(), err))
		return errors.New(fmt.Sprintf("%s:binary path add in /etc/profile, error:%s", p.Name(), err))
	}
	p.runtime.Logger.Info("startup process successfully")
	return nil
}

// Retry 重试
func (p *PredixyInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (p *PredixyInstall) Rollback() error {
	return nil
}
