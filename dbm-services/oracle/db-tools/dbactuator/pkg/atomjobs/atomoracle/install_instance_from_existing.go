package atomoracle

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
	"github.com/shirou/gopsutil/v3/mem"
)

// InstallInstanceFromExistingParams 执行脚本初始化参数
type InstallInstanceFromExistingParams struct {
	LogArchiveConfig      string `json:"log_archive_config" validate:"required"`
	OracleSID             string `json:"oracle_sid" validate:"required"`
	CfSsn                 string `json:"cf_ssn"`
	CfSchema              string `json:"cf_schema"`
	Pfile                 string `json:"pfile" validate:"required"`
	Orapw                 string `json:"orapw" validate:"required"`
	MasterHost            string `json:"master_host" validate:"required,ip"`
	SlaveHost             string `json:"slave_host" validate:"required,ip"`
	MasterDbUniqueName    string `json:"master_db_unique_name" validate:"required"`
	SlaveDbUniqueName     string `json:"slave_db_unique_name" validate:"required"`
	OldMasterHost         string `json:"old_master_host"`
	OldMasterDbUniqueName string `json:"old_master_db_unique_name"`
}

// InstallInstanceFromExisting 执行脚本原子任务   root用户执行
type InstallInstanceFromExisting struct {
	BaseJob
	Params                                *InstallInstanceFromExistingParams
	InstallInstanceFromExistingRunTimeCtx `json:"-"`
}

type InstallInstanceFromExistingRunTimeCtx struct {
	TotalGB            uint64 `json:"total_gb"`
	SgaGB              uint64 `json:"sga_gb"`
	PgaGB              uint64 `json:"pga_gb"`
	Shmall             uint64 `json:"shmall"`
	Shmmax             uint64 `json:"shmmax"`
	Hugepages          uint64 `json:"hugepages"`
	DbRecoveryFileDest string `json:"db_recovery_file_dest"`
	LogArchiveConfig   string `json:"log_archive_config"`
	FailoverServer     string `json:"failover_server"`
}

// NewInstallInstanceFromExisting new
func NewInstallInstanceFromExisting() jobruntime.JobRunner {
	return &InstallInstanceFromExisting{}
}

// pfileEntry 描述一条 pfile 参数的修改意图
// 语义：确保 pfile 中存在 `<key>=<val>`（存在则替换，不存在则追加）
type pfileEntry struct {
	key    string // 完整 key，如 "*.sga_target" 或 "CFDBHAYLEY.__sga_target"
	val    string // 值的字符串形式（数字请先用 strconv.FormatUint 转换）
	quoted bool   // true=值加单引号包裹（字符串类型），false=裸值（数字类型）
}

// Init 初始化
func (e *InstallInstanceFromExisting) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of InstallInstanceFromExisting fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of InstallInstanceFromExisting fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *InstallInstanceFromExisting) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of InstallInstanceFromExisting")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of InstallInstanceFromExisting fail, error:%s", err)
		return fmt.Errorf("validate parameters of InstallInstanceFromExisting fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *InstallInstanceFromExisting) Name() string {
	return "install-instance-from-existing"
}

// Run 执行函数
func (e *InstallInstanceFromExisting) Run() error {
	e.Runtime.Logger.Info("start to install instance from existing")
	if err := e.PreCheck(); err != nil {
		return err
	}
	// 根据本机物理内存计算 SGA / PGA 大小
	err := e.GetInstMemByIP()
	if err != nil {
		return err
	}
	// 计算 sysctl 内核参数
	e.CalcKernelParams()
	// 写入 /etc/sysctl.conf 并生效
	if err = e.ApplyKernelParams(); err != nil {
		return err
	}
	if err = e.CopyOrapw(); err != nil {
		return err
	}
	// 修改pfile中参数
	if err = e.ModifyPfile(); err != nil {
		return err
	}
	// 生成spfile
	if err = e.CreateSpfile(); err != nil {
		return err
	}
	if err = e.StartInstance(); err != nil {
		return err
	}
	if err = e.StartStatisticListener(); err != nil {
		return err
	}
	if err = e.ConfigTnsNames(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("install instance from existing successfully")
	return nil
}

// renderShell 生成本条参数对应的 shell 语句：存在则 sed 替换、不存在则 echo 追加
func (p pfileEntry) renderShell(pfile string) string {
	if p.quoted {
		return fmt.Sprintf(`
if grep -qE '^[[:space:]]*\%s[[:space:]]*=' %s; then
	sed -i -E "s|^([[:space:]]*\%s[[:space:]]*=).*|\1'%s'|" %s
else
	echo "%s='%s'" >> %s
fi`, p.key, pfile, p.key, p.val, pfile, p.key, p.val, pfile)
	}
	return fmt.Sprintf(`
if grep -qE '^[[:space:]]*\%s[[:space:]]*=' %s; then
	sed -i -E "s|^([[:space:]]*\%s[[:space:]]*=).*|\1%s|" %s
else
	echo "%s=%s" >> %s
fi`, p.key, pfile, p.key, p.val, pfile, p.key, p.val, pfile)
}

// PreCheck 预检查
func (e *InstallInstanceFromExisting) PreCheck() error {
	real, err := filepath.EvalSymlinks(consts.ArchPath)
	if err != nil {
		e.Runtime.Logger.Error("resolve %s fail: %s", consts.ArchPath, err)
		return fmt.Errorf("db_recovery_file_dest is empty and resolve %s fail: %s",
			consts.ArchPath, err)
	}
	info, err := os.Stat(real)
	if err != nil {
		e.Runtime.Logger.Error("stat resolved path %s fail: %s", real, err)
		return fmt.Errorf("db_recovery_file_dest is empty, resolved %s -> %s does not exist: %s",
			consts.ArchPath, real, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("db_recovery_file_dest is empty, resolved %s -> %s is not a directory",
			consts.ArchPath, real)
	}
	e.Runtime.Logger.Info("db_recovery_file_dest is empty, fallback to %s -> %s",
		consts.ArchPath, real)
	e.DbRecoveryFileDest = real
	return nil
}

func (e *InstallInstanceFromExisting) CopyOrapw() error {
	orapwFile := filepath.Join(consts.DefaultOracleHome, "dbs", fmt.Sprintf("orapw%s", e.Params.OracleSID))
	cmd := fmt.Sprintf("cp -p %s %s", e.Params.Orapw, orapwFile)
	out, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		e.Runtime.Logger.Error("copy orapw fail: %s, output: %s", err, out)
		return fmt.Errorf("copy orapw fail: %s, output: %s", err, out)
	}
	e.Runtime.Logger.Info("copy orapw successfully, output:\n%s", out)
	return nil
}

// CreateSpfile 常见spfile
func (e *InstallInstanceFromExisting) CreateSpfile() error {
	// 先记录 pfile 的存在性/属主/大小等信息, 便于偶发失败时定位
	if fi, statErr := os.Stat(e.Params.Pfile); statErr != nil {
		e.Runtime.Logger.Warn("create spfile: stat pfile(%s) fail: %s", e.Params.Pfile, statErr)
	} else {
		e.Runtime.Logger.Info("create spfile: pfile=%s size=%d mode=%s", e.Params.Pfile, fi.Size(), fi.Mode())
	}
	// 确认 spfile 目标路径是否已存在残留
	spfilePath := filepath.Join(consts.DefaultOracleHome, "dbs", fmt.Sprintf("spfile%s.ora", e.Params.OracleSID))
	if fi, statErr := os.Stat(spfilePath); statErr == nil {
		e.Runtime.Logger.Warn("create spfile: existing spfile found: %s size=%d mode=%s", spfilePath, fi.Size(), fi.Mode())
	}

	// 目标 spfile 可能正被已启动实例占用（ORA-32002）。
	// 先尝试 shutdown abort 关闭实例，忽略"未启动"类错误；再把残留 spfile 备份改名，最后重建。
	shutdownCmd := fmt.Sprintf(`su - %s -c "sqlplus -S / as sysdba <<'EOF'
WHENEVER SQLERROR CONTINUE;
SHUTDOWN ABORT;
EXIT;
EOF"`, consts.OracleAccount)
	if out, err := util.RunBashCmd(shutdownCmd, "", nil, 2*time.Minute); err != nil {
		// 实例本身未启动时 sqlplus 也可能非零退出，这里只告警不阻断
		e.Runtime.Logger.Warn("create spfile: shutdown abort returned err=%s, output=%s", err, out)
	} else {
		e.Runtime.Logger.Info("create spfile: shutdown abort output:\n%s", out)
	}

	// 备份并移除残留 spfile，避免 ORA-32002 或后续启动误加载旧 spfile
	if _, statErr := os.Stat(spfilePath); statErr == nil {
		backupCmd := fmt.Sprintf(`su - %s -c "mv -f %s %s.bak.$(date +%%Y%%m%%d%%H%%M%%S)"`,
			consts.OracleAccount, spfilePath, spfilePath)
		if out, err := util.RunBashCmd(backupCmd, "", nil, 30*time.Second); err != nil {
			e.Runtime.Logger.Error("create spfile: backup existing spfile fail: %s, output: %s", err, out)
			return fmt.Errorf("create spfile: backup existing spfile fail: %s, output: %s", err, out)
		}
		e.Runtime.Logger.Info("create spfile: existing spfile %s backed up", spfilePath)
	}

	cmd := fmt.Sprintf(`su - %s -c "sqlplus -S / as sysdba <<'EOF'
WHENEVER SQLERROR EXIT SQL.SQLCODE;
CREATE SPFILE FROM PFILE='%s';
EXIT;
EOF"`, consts.OracleAccount, e.Params.Pfile)

	out, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		e.Runtime.Logger.Error("create spfile fail: err=%s, sqlplus_output=%q, cmd=%s", err, out, cmd)
		return fmt.Errorf("create spfile fail: %s, sqlplus_output: %s", err, out)
	}
	e.Runtime.Logger.Info("create spfile successfully, output:\n%s", out)
	return nil
}

// StartInstance 启动实例到 nomount 并校验状态
func (e *InstallInstanceFromExisting) StartInstance() error {
	cmd := fmt.Sprintf(`su - %s -c "sqlplus -S / as sysdba <<'EOF'
WHENEVER SQLERROR EXIT SQL.SQLCODE;
STARTUP NOMOUNT;
SET HEADING OFF FEEDBACK OFF PAGESIZE 0;
SELECT status FROM v\$instance;
EXIT;
EOF"`, consts.OracleAccount)

	out, err := util.RunBashCmd(cmd, "", nil, 5*time.Minute)
	if err != nil {
		e.Runtime.Logger.Error("startup nomount fail: %s, output: %s", err, out)
		return fmt.Errorf("startup nomount fail: %s, output: %s", err, out)
	}
	e.Runtime.Logger.Info("startup nomount output:\n%s", out)
	upper := strings.ToUpper(out)
	if !strings.Contains(upper, "ORACLE INSTANCE STARTED") {
		return fmt.Errorf("instance not started, sqlplus output: %s", out)
	}
	if !strings.Contains(upper, "STARTED") {
		return fmt.Errorf("instance status is not STARTED, sqlplus output: %s", out)
	}
	return nil
}

// StartStatisticListener 创建并启动静态监听 LISTENER1（1522 端口）
func (e *InstallInstanceFromExisting) StartStatisticListener() error {
	sid := e.Params.OracleSID
	host := e.Params.SlaveHost
	listenerFile := consts.DefaultOracleHome + "/network/admin/listener.ora"
	listenerName := "LISTENER1"

	e.Runtime.Logger.Info("start to configure static listener")

	tplBytes, err := staticembed.StatisticListener.ReadFile(staticembed.StatisticListenerFileName)
	if err != nil {
		return fmt.Errorf("read embedded %s fail: %s", staticembed.StatisticListenerFileName, err)
	}

	content := strings.NewReplacer(
		"{{oracle_sid}}", sid,
		"{{oracle_home}}", consts.DefaultOracleHome,
		"{{host}}", host,
	).Replace(string(tplBytes))

	if err = common.CreateFileAndChown(e.Runtime, listenerFile, []byte(content),
		consts.OracleAccount, consts.OracleGroup, 0644); err != nil {
		return err
	}
	e.Runtime.Logger.Info("write listener.ora successfully, content:\n%s", content)

	cmd := []string{
		fmt.Sprintf(`su - %s -c 'lsnrctl stop %s'`, consts.OracleAccount, listenerName),
		fmt.Sprintf(`su - %s -c 'lsnrctl start %s'`, consts.OracleAccount, listenerName),
		fmt.Sprintf(`su - %s -c 'lsnrctl status %s'`, consts.OracleAccount, listenerName),
	}
	for _, c := range cmd {
		out, err := util.RunBashCmd(c, "", nil, 30*time.Second)
		if strings.Contains(c, "stop") {
			continue
		}
		if err != nil {
			e.Runtime.Logger.Error("run cmd %s fail: %s", c, err)
			return fmt.Errorf("run cmd %s fail: %s", c, err)
		}
		if !strings.Contains(out, "The command completed successfully") {
			return fmt.Errorf("no [success] key in ouput: %s, cmd: %s", out, c)
		}
		e.Runtime.Logger.Info("run cmd %s successfully, output:\n%s", c, out)
	}
	return nil
}

// ConfigTnsNames 配置tnsnames.ora
func (e *InstallInstanceFromExisting) ConfigTnsNames() error {
	e.Runtime.Logger.Info("start to config tnsnames.ora")

	oracleHome := os.Getenv("ORACLE_HOME")
	if oracleHome == "" {
		oracleHome = consts.DefaultOracleHome
	}
	tnsFile := oracleHome + "/network/admin/" + staticembed.TnsNamesFileName

	tplBytes, err := staticembed.TnsNames.ReadFile(staticembed.TnsNamesFileName)
	if err != nil {
		e.Runtime.Logger.Error("read embedded %s fail, error:%s", staticembed.TnsNamesFileName, err)
		return fmt.Errorf("read embedded %s fail, error:%s", staticembed.TnsNamesFileName, err)
	}

	content := strings.NewReplacer(
		"{{db_unique_name}}", e.Params.SlaveDbUniqueName,
		"{{host}}", e.Params.SlaveHost,
		"{{port}}", strconv.Itoa(consts.StatisticListenerPort),
		"{{oracle_sid}}", e.Params.OracleSID,
	).Replace(string(tplBytes))

	contentMaster := strings.NewReplacer(
		"{{db_unique_name}}", e.Params.MasterDbUniqueName,
		"{{host}}", e.Params.MasterHost,
		"{{port}}", strconv.Itoa(consts.ListenerPort),
		"{{oracle_sid}}", e.Params.OracleSID,
	).Replace(string(tplBytes))

	// 追加写入，避免覆盖已有条目；文件不存在则创建
	f, err := os.OpenFile(tnsFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		e.Runtime.Logger.Error("open %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("open %s fail, error:%s", tnsFile, err)
	}
	err = cmutil.Chown(tnsFile, consts.OracleAccount, consts.OracleGroup)
	if err != nil {
		e.Runtime.Logger.Error("chown %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("chown %s fail, error:%s", tnsFile, err)
	}
	defer f.Close()
	if _, err = f.WriteString(content + "\n"); err != nil {
		e.Runtime.Logger.Error("append content to %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("append content to %s fail, error:%s", tnsFile, err)
	}
	e.Runtime.Logger.Info("config tnsnames.ora successfully, file:%s, appended content:\n%s", tnsFile, content)

	if _, err = f.WriteString(contentMaster + "\n"); err != nil {
		e.Runtime.Logger.Error("append content to %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("append content to %s fail, error:%s", tnsFile, err)
	}
	e.Runtime.Logger.Info("config tnsnames.ora successfully, file:%s, appended content:\n%s", tnsFile, contentMaster)
	// tnsping 校验连通性
	if err = TnsPing(e.Params.SlaveDbUniqueName); err != nil {
		return err
	}
	if err = TnsPing(e.Params.MasterDbUniqueName); err != nil {
		return err
	}

	if e.Params.OldMasterDbUniqueName != "" {
		contentOldMaster := strings.NewReplacer(
			"{{db_unique_name}}", e.Params.OldMasterDbUniqueName,
			"{{host}}", e.Params.OldMasterHost,
			"{{port}}", strconv.Itoa(consts.ListenerPort),
			"{{oracle_sid}}", e.Params.OracleSID,
		).Replace(string(tplBytes))
		if _, err = f.WriteString(contentOldMaster + "\n"); err != nil {
			e.Runtime.Logger.Error("append content to %s fail, error:%s", tnsFile, err)
			return fmt.Errorf("append content to %s fail, error:%s", tnsFile, err)
		}
		e.Runtime.Logger.Info("config tnsnames.ora successfully, file:%s, appended content:\n%s", tnsFile, contentOldMaster)
		if err = TnsPing(e.Params.OldMasterDbUniqueName); err != nil {
			return err
		}
	}
	return nil
}

// GetInstMemByIP 根据本机物理内存计算 Oracle 实例可用的 SGA / PGA 大小
// 计算规则：availMem(MB) = 物理内存 * 60%；SGA = availMem * 2/3；PGA = availMem * 1/3
// 返回值单位：均为整数 GB（向下取整）；totalGB 为物理总内存
func (e *InstallInstanceFromExisting) GetInstMemByIP() (err error) {
	vMem, err := mem.VirtualMemory()
	if err != nil {
		return err
	}
	kilo := uint64(1024)
	totalMemInMi := vMem.Total / kilo / kilo
	totalGB := totalMemInMi / kilo
	availMem := int64(float64(totalMemInMi) * 0.6)
	sgaGB := uint64(availMem) * 2 / 3 / 1024
	pgaGB := uint64(availMem) / 3 / 1024

	if sgaGB == 0 || pgaGB == 0 {
		return fmt.Errorf("sgaGB or pgaGB is 0, sgaGB: %d, pgaGB: %d, "+
			"totalMemInMi: %d, availMem: %d", sgaGB, pgaGB, totalMemInMi, availMem)
	}
	e.Runtime.Logger.Info("mem calc: totalGB=%d, sgaGB=%d, pgaGB=%d", totalGB, sgaGB, pgaGB)
	e.InstallInstanceFromExistingRunTimeCtx.TotalGB = totalGB
	e.InstallInstanceFromExistingRunTimeCtx.SgaGB = sgaGB
	e.InstallInstanceFromExistingRunTimeCtx.PgaGB = pgaGB
	return nil
}

// CalcKernelParams 依据物理内存(GB) 与 SGA(GB) 计算 Oracle 相关的 sysctl 内核参数
//
//	shmall    = totalGB * 0.8 * 1GB / 4KB  (整数, 单位: 4KB 页数)
//	shmmax    = shmall * 4096              (字节)
//	hugepages = (sga + 2) * 1024 / 2       (2MB 大页数)
func (e *InstallInstanceFromExisting) CalcKernelParams() {
	// 先乘后除，最大化保留精度
	e.InstallInstanceFromExistingRunTimeCtx.Shmall = e.InstallInstanceFromExistingRunTimeCtx.TotalGB * 4 * 1024 * 1024 * 1024 / 5 / 4096
	e.InstallInstanceFromExistingRunTimeCtx.Shmmax = e.InstallInstanceFromExistingRunTimeCtx.Shmall * 4096
	e.InstallInstanceFromExistingRunTimeCtx.Hugepages = (e.InstallInstanceFromExistingRunTimeCtx.SgaGB + 2) * 512
	return
}

// ApplyKernelParams 将 shmall / shmmax / vm.nr_hugepages 写入 /etc/sysctl.conf 并执行生效
func (e *InstallInstanceFromExisting) ApplyKernelParams() error {
	e.Runtime.Logger.Info("start to apply kernel params to /etc/sysctl.conf")
	// 三个 key 一起处理，%s 中的 key 已通过 shell 转义为字面量
	cmd := fmt.Sprintf(`set -e
sed -i -E '/^[[:space:]]*kernel\.shmmax[[:space:]]*=/d' /etc/sysctl.conf
sed -i -E '/^[[:space:]]*kernel\.shmall[[:space:]]*=/d' /etc/sysctl.conf
sed -i -E '/^[[:space:]]*vm\.nr_hugepages[[:space:]]*=/d' /etc/sysctl.conf
echo "kernel.shmmax = %d" >> /etc/sysctl.conf
echo "kernel.shmall = %d" >> /etc/sysctl.conf
echo "vm.nr_hugepages = %d" >> /etc/sysctl.conf
sysctl -p
sysctl kernel.shmmax kernel.shmall vm.nr_hugepages
`, e.InstallInstanceFromExistingRunTimeCtx.Shmmax, e.InstallInstanceFromExistingRunTimeCtx.Shmall,
		e.InstallInstanceFromExistingRunTimeCtx.Hugepages)

	out, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		e.Runtime.Logger.Error("apply kernel params fail: %s, output: %s", err, out)
		return fmt.Errorf("apply kernel params fail: %s", err)
	}
	e.Runtime.Logger.Info("apply kernel params successfully, sysctl output:\n%s", out)
	return nil
}

// ModifyPfile 修改 pfile 中的参数
// 所有参数统一采用「存在则替换、不存在则追加」模式
func (e *InstallInstanceFromExisting) ModifyPfile() error {
	pfile := e.Params.Pfile
	sid := e.Params.OracleSID
	// SGA / PGA 单位：字节
	sgaBytes := strconv.FormatUint(e.InstallInstanceFromExistingRunTimeCtx.SgaGB*1024*1024*1024, 10)
	pgaBytes := strconv.FormatUint(e.InstallInstanceFromExistingRunTimeCtx.PgaGB*1024*1024*1024, 10)
	fraSize := strconv.FormatUint(consts.DbRecoveryFileDestSize, 10)
	e.Runtime.Logger.Info("start to modify pfile: %s, db_unique_name=%s, sgaBytes=%s, pgaBytes=%s",
		pfile, e.Params.SlaveDbUniqueName, sgaBytes, pgaBytes)
	var logArchiveConfig string
	var err error
	if e.Params.OldMasterDbUniqueName != "" {
		logArchiveConfig, err = AppendDgConfigMember(e.Params.LogArchiveConfig, e.Params.OldMasterDbUniqueName)
		if err != nil {
			return err
		}
	}
	logArchiveConfig, err = AppendDgConfigMember(e.Params.LogArchiveConfig, e.Params.SlaveDbUniqueName)
	if err != nil {
		return err
	}
	e.LogArchiveConfig = logArchiveConfig
	if e.Params.OldMasterDbUniqueName == "" {
		e.FailoverServer = e.Params.MasterDbUniqueName
	} else {
		e.FailoverServer = e.Params.OldMasterDbUniqueName
	}

	// 声明所有待修改的 pfile 参数
	entries := []pfileEntry{
		// DG 相关
		{"*.log_archive_config", e.LogArchiveConfig, true},
		// {"*.fal_client", e.Params.FalClient, true},
		{"*.fal_client", e.Params.SlaveDbUniqueName, true},
		// {"*.fal_server", e.Params.FalServer, true},
		{"*.fal_server", e.FailoverServer, true},
		// 命名
		{"*.db_unique_name", e.Params.SlaveDbUniqueName, true},
		// SGA：*. 与 SID.__ 两种前缀均处理
		{"*.sga_max_size", sgaBytes, false},
		{"*.sga_target", sgaBytes, false},
		{sid + ".__sga_target", sgaBytes, false},
		// PGA：*. 与 SID.__ 两种前缀均处理
		{"*.pga_aggregate_target", pgaBytes, false},
		{sid + ".__pga_aggregate_target", pgaBytes, false},
		// 归档 / FRA / 备库
		{"*.log_archive_dest_1", "LOCATION=USE_DB_RECOVERY_FILE_DEST", true},
		{"*.db_recovery_file_dest", e.DbRecoveryFileDest, true},
		{"*.db_recovery_file_dest_size", fraSize, false},
		{"*.standby_archive_dest", "LOCATION=USE_DB_RECOVERY_FILE_DEST", true},
		{"*.standby_file_management", "AUTO", true},
	}

	// 空值短路：任何 entry 的值缺失都直接报错，避免污染 pfile
	// - 字符串类型（quoted=true）：val=="" 视为无效
	// - 数字类型（quoted=false）：val=="0" 或 "" 均视为无效（0 通常是未设置的哨兵值）
	var missing []string
	for _, entry := range entries {
		if entry.val == "" || (!entry.quoted && entry.val == "0") {
			missing = append(missing, entry.key)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("modify pfile fail: the following parameters are empty or invalid: %s",
			strings.Join(missing, ", "))
	}

	// 拼接 shell：set -e + 备份 + 遍历参数生成 upsert 语句
	var b strings.Builder
	b.WriteString("set -e\n")
	// 备份原 pfile：同目录下生成 <pfile>.bak.YYYYMMDDHHMMSS
	b.WriteString(fmt.Sprintf("cp -p %s %s.bak.$(date +%%Y%%m%%d%%H%%M%%S)\n", pfile, pfile))
	for _, entry := range entries {
		b.WriteString(entry.renderShell(pfile))
		b.WriteString("\n")
	}
	cmd := b.String()

	e.Runtime.Logger.Info("modify pfile cmd:\n%s", cmd)
	out, err := util.RunBashCmd(cmd, "", nil, 30*time.Second)
	if err != nil {
		e.Runtime.Logger.Error("modify pfile fail: %s, output: %s", err, out)
		return fmt.Errorf("modify pfile fail: %s", err)
	}
	e.Runtime.Logger.Info("modify pfile successfully, output:\n%s", out)
	return nil
}
