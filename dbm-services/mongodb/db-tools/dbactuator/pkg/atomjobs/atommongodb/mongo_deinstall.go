package atommongodb

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/common"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/util"
	"dbm-services/mongodb/db-tools/dbmon/pkg/linuxproc"

	"github.com/go-playground/validator/v10"
)

// DeInstallConfParams 参数
type DeInstallConfParams struct {
	IP           string   `json:"ip" validate:"required"`
	Port         int      `json:"port" validate:"required"`
	SetId        string   `json:"setId"`
	NodeInfo     []string `json:"nodeInfo" validate:"required"`     // []string ip,ip  如果为复制集节点，则为复制集所有节点的ip；如果为mongos，则为mongos的ip
	InstanceType string   `json:"instanceType" validate:"required"` // mongod mongos
	Force        bool     `json:"force"`                            // 不检查连接，强制卸载
	RenameDir    bool     `json:"renameDir"`                        // 关闭进程后是否重命名目录 true 重命名目录，false 不重命名目录
}

// DeInstall 添加分片到集群
type DeInstall struct {
	BaseJob
	runtime          *jobruntime.JobGenericRuntime
	BinDir           string
	DataDir          string
	BackupDir        string
	DbpathDir        string
	InstallPath      string
	PortDir          string
	LogPortDir       string
	DbPathRenameDir  string
	LogPathRenameDir string
	Mongo            string
	OsUser           string
	ServiceStatus    bool
	IPInfo           string
	ConfParams       *DeInstallConfParams
}

// NewDeInstall 实例化结构体
func NewDeInstall() jobruntime.JobRunner {
	return &DeInstall{}
}

// Name 获取原子任务的名字
func (d *DeInstall) Name() string {
	return "mongo_deinstall"
}

// Run 运行原子任务
func (d *DeInstall) Run() error {
	// 检查实例状态
	if err := d.checkMongoService(); err != nil {
		return err
	}

	// 关闭进程
	if err := d.shutdownProcess(); err != nil {
		return err
	} else {
		d.runtime.Logger.Info("shutdown service successfully")
	}

	// rename目录
	if err := d.DirRename(); err != nil {
		return err
	}

	return nil
}

// Retry 重试
func (d *DeInstall) Retry() uint {
	return 2
}

// Rollback 回滚
func (d *DeInstall) Rollback() error {
	return nil
}

// Init 初始化
func (d *DeInstall) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	d.runtime = runtime
	d.runtime.Logger.Info("start to init")
	d.BinDir = consts.GetMongoBinDir()
	d.DataDir = consts.GetMongoDataDir()
	d.BackupDir = consts.GetMongoBackupDir()

	d.OsUser = consts.GetProcessUser()

	// 获取MongoDB配置文件参数
	if err := json.Unmarshal([]byte(d.runtime.PayloadDecoded), &d.ConfParams); err != nil {
		d.runtime.Logger.Error(
			"get parameters of deInstall fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of deInstall fail by json.Unmarshal, error:%s", err)
	}

	// 获取各种目录
	d.InstallPath = filepath.Join(d.BinDir, "mongodb")
	d.Mongo = filepath.Join(d.BinDir, "mongodb", "bin", "mongo")
	strPort := strconv.Itoa(d.ConfParams.Port)
	d.PortDir = filepath.Join(d.DataDir, "mongodata", strPort)
	d.DbpathDir = filepath.Join(d.DataDir, "mongodata", strPort, "db")
	strTime := time.Now().Format("20060102150405")
	renameDirName := fmt.Sprintf("removed_%d_%s", d.ConfParams.Port, strTime)
	d.DbPathRenameDir = filepath.Join(d.DataDir, "mongodata", renameDirName)
	d.LogPathRenameDir = filepath.Join(d.BackupDir, "mongolog", renameDirName)
	d.IPInfo = strings.Join(d.ConfParams.NodeInfo, "|")
	d.LogPortDir = filepath.Join(d.BackupDir, "mongolog", strPort)

	// 进行校验
	if err := d.checkParams(); err != nil {
		return err
	}

	return nil
}

// checkParams 校验参数
func (d *DeInstall) checkParams() error {
	// 校验配置参数
	d.runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	d.runtime.Logger.Info("start to validate parameters of deInstall")
	if err := validate.Struct(d.ConfParams); err != nil {
		d.runtime.Logger.Error("validate parameters of deInstall fail, error:%s", err)
		return fmt.Errorf("validate parameters of deInstall fail, error:%s", err)
	}
	return nil
}

// checkMongoService 检查mongo服务
func (d *DeInstall) checkMongoService() error {
	d.runtime.Logger.Info("start to check process status")
	flag, _, err := common.CheckMongoService(d.ConfParams.Port)
	if err != nil {
		d.runtime.Logger.Error("get mongo service status fail, error:%s", err)
		return fmt.Errorf("get mongo service status fail, error:%s", err)
	}
	d.ServiceStatus = flag
	return nil
}

// checkConnection 检查是否仍有外部客户端连到本机 Mongo 端口。
// 读取 /proc/net/tcp（IPv4），排除回环与 NodeInfo 中的节点 IP；若仍有外部 ESTABLISHED 连接则失败，
// 并打印 来源IP:PORT、目标IP:PORT、连接数量。
func (d *DeInstall) checkConnection() error {
	d.runtime.Logger.Info("start to check connection via /proc/net/tcp")

	rows, err := linuxproc.ProcNetTcp(nil)
	if err != nil {
		d.runtime.Logger.Error("check connection fail, read /proc/net/tcp error:%s", err)
		return fmt.Errorf("check connection fail, read /proc/net/tcp error:%s", err)
	}

	excludeIPs := map[string]struct{}{
		"0.0.0.0":   {},
		"127.0.0.1": {},
	}
	for _, ip := range d.ConfParams.NodeInfo {
		if ip = strings.TrimSpace(ip); ip != "" {
			excludeIPs[ip] = struct{}{}
		}
	}
	if ip := strings.TrimSpace(d.ConfParams.IP); ip != "" {
		excludeIPs[ip] = struct{}{}
	}

	// key: "sourceIP:sourcePort -> targetIP:targetPort" -> count
	counts := make(map[string]int)
	for _, row := range rows {
		if row.LocalPort != d.ConfParams.Port || row.St != linuxproc.ESTABLISHED {
			continue
		}
		if row.RemoteHost == "" || row.RemotePort == 0 {
			continue
		}
		if _, skip := excludeIPs[row.RemoteHost]; skip {
			continue
		}
		src := fmt.Sprintf("%s:%d", row.RemoteHost, row.RemotePort)
		dst := fmt.Sprintf("%s:%d", row.LocalHost, row.LocalPort)
		counts[fmt.Sprintf("%s -> %s", src, dst)]++
	}

	if len(counts) == 0 {
		return nil
	}

	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		if counts[keys[i]] != counts[keys[j]] {
			return counts[keys[i]] > counts[keys[j]]
		}
		return keys[i] < keys[j]
	})

	var b strings.Builder
	total := 0
	for _, k := range keys {
		n := counts[k]
		total += n
		parts := strings.SplitN(k, " -> ", 2)
		src, dst := parts[0], parts[1]
		line := fmt.Sprintf("count=%d source=%s target=%s", n, src, dst)
		d.runtime.Logger.Error("external connection: %s", line)
		if b.Len() > 0 {
			b.WriteByte('\n')
		}
		b.WriteString(line)
	}
	msg := fmt.Sprintf("check connection fail, external connections=%d:\n%s", total, b.String())
	d.runtime.Logger.Error("%s", msg)
	return fmt.Errorf("%s", msg)
}

// shutdownProcess 关闭进程
func (d *DeInstall) shutdownProcess() error {
	if d.ServiceStatus == true {
		d.runtime.Logger.Info("start to shutdown service")
		// 检查连接
		if d.ConfParams.Force == false {
			if err := d.checkConnection(); err != nil {
				return err
			}
		}

		// 关闭进程（deinstall场景: 30秒未退出则kill -9兜底）
		if err := common.ShutdownMongoProcess(
			d.runtime.Logger,
			d.ConfParams.Port,
			30*time.Second,
			true,
		); err != nil {
			d.runtime.Logger.Error("shutdown mongo service fail, error:%s", err)
			return fmt.Errorf("shutdown mongo service fail, error:%s", err)
		}
	}

	return nil
}

// DirRename 打包数据目录
func (d *DeInstall) DirRename() error {
	// renameDb数据目录
	// 关闭进程后不重命名目录
	if d.ConfParams.RenameDir == false {
		d.runtime.Logger.Info("rename directory is disabled")
		return nil
	}
	flag := util.FileExists(d.PortDir)
	if flag == true {
		d.runtime.Logger.Info("start to rename db directory %s to %s", d.PortDir, d.DbPathRenameDir)
		if _, err := mycmd.New("mv", d.PortDir, d.DbPathRenameDir).Run(60 * time.Second); err != nil {
			d.runtime.Logger.Error("rename db directory fail, error:%s", err)
			return fmt.Errorf("rename db directory fail, error:%s", err)
		}
	} else {
		d.runtime.Logger.Info("db directory %s not exists, skip rename", d.PortDir)
	}

	// renameDb日志目录
	flag = util.FileExists(d.LogPortDir)
	if flag == true {
		d.runtime.Logger.Info("start to rename log directory %s to %s", d.LogPortDir, d.LogPathRenameDir)
		if _, err := mycmd.New("mv", d.LogPortDir, d.LogPathRenameDir).Run(60 * time.Second); err != nil {
			d.runtime.Logger.Error("rename log directory fail, error:%s", err)
			return fmt.Errorf("rename log directory fail, error:%s", err)
		}
	} else {
		d.runtime.Logger.Info("log directory %s not exists, skip rename", d.LogPortDir)
	}

	return nil
}
