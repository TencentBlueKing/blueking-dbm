package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"os/user"
	"strconv"
	"strings"

	"github.com/go-playground/validator/v10"
)

// ConfigDataguardParams 执行脚本初始化参数
type ConfigDataguardParams struct {
	LogArchiveConfig    string `json:"log_archive_config" validate:"required"`
	AvailableNumber     int    `json:"available_number" validate:"required"`
	LogArchiveDestState string `json:"log_archive_dest_state" validate:"required"`
	SlaveHost           string `json:"slave_host" validate:"required"`
	SlavePort           int    `json:"slave_port" validate:"required"`
	OracleSID           string `json:"oracle_sid" validate:"required"`
	SlaveDbUniqueName   string `json:"slave_db_unique_name" validate:"required"`
	RealMaster          bool   `json:"real_master"`
}

// ConfigDataguard 执行脚本原子任务   root用户执行
type ConfigDataguard struct {
	BaseJob
	Params                    *ConfigDataguardParams
	ConfigDataguardRunTimeCtx `json:"-"`
}

// ConfigDataguardRunTimeCtx 运行时上下文
type ConfigDataguardRunTimeCtx struct {
}

// NewConfigDataguard new
func NewConfigDataguard() jobruntime.JobRunner {
	return &ConfigDataguard{}
}

// Init 初始化
func (e *ConfigDataguard) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of ConfigDataguard fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of ConfigDataguard fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *ConfigDataguard) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of ConfigDataguard")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of ConfigDataguard fail, error:%s", err)
		return fmt.Errorf("validate parameters of ConfigDataguard fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *ConfigDataguard) Name() string {
	return "config-dataguard"
}

// Run 执行函数
func (e *ConfigDataguard) Run() error {
	if err := e.ConfigTnsNames(); err != nil {
		return err
	}
	if err := e.ConfigDataguard(); err != nil {
		return err
	}
	return nil
}

// buildDataguardStmts 根据 dataguard 参数拼接需要执行的 ALTER SYSTEM SQL 列表。
func buildDataguardStmts(logArchiveConfig string, availableNumber int, slaveDbUniqueName string, realMaster bool,
	logArchiveDestState string) []string {
	validFor := "VALID_FOR=(ONLINE_LOGFILES,PRIMARY_ROLE)"
	if !realMaster {
		validFor = "VALID_FOR=(STANDBY_LOGFILES,STANDBY_ROLE)"
	}
	return []string{
		fmt.Sprintf("alter system set log_archive_config='%s'", logArchiveConfig),
		fmt.Sprintf("alter system set log_archive_dest_state_%d='%s'", availableNumber, logArchiveDestState),
		fmt.Sprintf("alter system set log_archive_dest_%d="+
			"'SERVICE=%s LGWR ASYNC NOAFFIRM %s DB_UNIQUE_NAME=%s REOPEN=30'",
			availableNumber, slaveDbUniqueName, validFor, slaveDbUniqueName),
	}
}

// ConfigDataguard 配置dataguard
func (e *ConfigDataguard) ConfigDataguard() error {
	e.Runtime.Logger.Info("start to config dataguard")
	db, err := common.OpenOracleAsSysdba()
	if err != nil {
		e.Runtime.Logger.Error("open oracle as sysdba fail, error:%s", err)
		return fmt.Errorf("open oracle as sysdba fail, error:%s", err)
	}
	defer db.Close()
	// 将新的 SlaveDbUniqueName 追加到原有 DG_CONFIG 列表中，避免覆盖已存在的其他成员
	newLogArchiveConfig, err := AppendDgConfigMember(e.Params.LogArchiveConfig, e.Params.SlaveDbUniqueName)
	if err != nil {
		e.Runtime.Logger.Error("append dg config member fail, error:%s", err)
		return fmt.Errorf("append dg config member fail, error:%s", err)
	}
	e.Runtime.Logger.Info("log_archive_config: origin=%s, new=%s",
		e.Params.LogArchiveConfig, newLogArchiveConfig)

	stmts := buildDataguardStmts(newLogArchiveConfig, e.Params.AvailableNumber, e.Params.SlaveDbUniqueName,
		e.Params.RealMaster, e.Params.LogArchiveDestState)
	for _, stmt := range stmts {
		e.Runtime.Logger.Info("execute sql:%s", stmt)
		if _, err = db.Exec(stmt); err != nil {
			e.Runtime.Logger.Error("execute sql:%s fail, error:%s", stmt, err)
			return fmt.Errorf("execute sql:%s fail, error:%s", stmt, err)
		}
	}
	e.Runtime.Logger.Info("config dataguard successfully")
	return nil
}

// ConfigTnsNames 配置tnsnames.ora
func (e *ConfigDataguard) ConfigTnsNames() error {
	e.Runtime.Logger.Info("start to config tnsnames.ora")

	oracleHome := os.Getenv("ORACLE_HOME")
	if oracleHome == "" {
		oracleHome = consts.DefaultOracleHome
	}
	tnsFile := oracleHome + consts.NetworkAdminSubPath + staticembed.TnsNamesFileName

	tplBytes, err := staticembed.TnsNames.ReadFile(staticembed.TnsNamesFileName)
	if err != nil {
		e.Runtime.Logger.Error("read embedded %s fail, error:%s", staticembed.TnsNamesFileName, err)
		return fmt.Errorf("read embedded %s fail, error:%s", staticembed.TnsNamesFileName, err)
	}

	content := strings.NewReplacer(
		consts.TnsPlaceholderDBUniqueName, e.Params.SlaveDbUniqueName,
		consts.TnsPlaceholderHost, e.Params.SlaveHost,
		consts.TnsPlaceholderPort, strconv.Itoa(e.Params.SlavePort),
		consts.TnsPlaceholderOracleSID, e.Params.OracleSID,
	).Replace(string(tplBytes))

	// 追加写入，避免覆盖已有条目；文件不存在则创建
	f, err := os.OpenFile(tnsFile, os.O_CREATE|os.O_APPEND|os.O_WRONLY, consts.TnsFilePerm)
	if err != nil {
		e.Runtime.Logger.Error("open %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("open %s fail, error:%s", tnsFile, err)
	}
	defer f.Close()
	if _, err = f.WriteString(content + "\n"); err != nil {
		e.Runtime.Logger.Error("append content to %s fail, error:%s", tnsFile, err)
		return fmt.Errorf("append content to %s fail, error:%s", tnsFile, err)
	}
	e.Runtime.Logger.Info("config tnsnames.ora successfully, file:%s, appended content:\n%s", tnsFile, content)

	// tnsping 校验连通性
	if err = TnsPing(e.Params.SlaveDbUniqueName); err != nil {
		return err
	}
	return nil
}

// TnsPing 执行 tnsping <name> 校验连通性
// 若当前进程已经是 oracle 用户则直接执行；否则通过 su - oracle -c 切换执行，
func TnsPing(name string) error {
	var cmd string
	if u, err := user.Current(); err == nil && u.Username == consts.OracleAccount {
		cmd = fmt.Sprintf(`tnsping %s`, name)
	} else {
		cmd = fmt.Sprintf(`su - %s -c 'tnsping %s'`, consts.OracleAccount, name)
	}
	out, err := util.RunBashCmd(cmd, "", nil, consts.TnsPingTimeout)
	if err != nil {
		return fmt.Errorf("run cmd %s fail, error:%s, output:%s", cmd, err, out)
	}
	if !strings.Contains(out, consts.TnsPingOKMarker) {
		return fmt.Errorf("tnsping %s fail, output:%s", name, out)
	}
	return nil
}

// AppendDgConfigMember 将 member 追加到 origin 中 DG_CONFIG=(...) 的括号内
// 例如: "DG_CONFIG=(A,B,C)" + "D"  =>  "DG_CONFIG=(A,B,C,D)"
// 若 member 已存在则原样返回；若 origin 不符合预期格式，则报错
func AppendDgConfigMember(origin, member string) (string, error) {
	rp := strings.LastIndex(origin, ")")
	originUpper := strings.ToUpper(origin)
	if rp < 0 || !strings.Contains(originUpper, consts.DgConfigPrefix) {
		return "", fmt.Errorf("origin %s is not a valid DG_CONFIG format", origin)
	}
	if strings.Contains(originUpper, strings.ToUpper(member)) {
		return origin, nil
	}
	return origin[:rp] + "," + member + origin[rp:], nil
}
