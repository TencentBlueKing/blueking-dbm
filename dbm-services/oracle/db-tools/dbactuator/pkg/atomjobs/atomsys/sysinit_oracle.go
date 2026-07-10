package atomsys

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs/atomoracle"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"

	"github.com/go-playground/validator/v10"
)

// SysInitCommandParams 系统初始化参数
// 说明：
//   - Password/OracleSid 必传。
//   - CfSsn/CfSchema 允许为空：为空时脚本会跳过对 .bash_profile 中 CF_SSN/CF_SCHEMA 的写入。
type SysInitCommandParams struct {
	Account   Account `json:"account"`
	OracleSid string  `json:"oracle_sid" validate:"required"`
	CfSsn     string  `json:"cf_ssn"`
	CfSchema  string  `json:"cf_schema"`
}

type Account struct {
	Username string `json:"username" validate:"required"`
	Password string `json:"password" validate:"required"`
}

// SysInitCommand 系统初始化原子任务（以 root 身份执行）
type SysInitCommand struct {
	atomoracle.BaseJob
	Params *SysInitCommandParams
}

// NewSysInitCommand new
func NewSysInitCommand() jobruntime.JobRunner {
	return &SysInitCommand{}
}

// Init 初始化
func (o *SysInitCommand) Init(runtime *jobruntime.JobGenericRuntime) error {
	o.Runtime = runtime
	o.Runtime.Logger.Info("start to init")

	// 解析入参
	o.Params = &SysInitCommandParams{}
	if err := json.Unmarshal([]byte(o.Runtime.PayloadDecoded), o.Params); err != nil {
		o.Runtime.Logger.Error("json unmarshal payload failed, err:%s", err.Error())
		return fmt.Errorf("json unmarshal payload failed, err:%s", err.Error())
	}
	if err := validator.New().Struct(o.Params); err != nil {
		o.Runtime.Logger.Error("validate params failed, err:%s", err.Error())
		return fmt.Errorf("validate params failed, err:%s", err.Error())
	}
	return nil
}

// Name 名字
func (o *SysInitCommand) Name() string {
	return "sysinit"
}

// Run 执行函数
func (o *SysInitCommand) Run() error {
	o.Runtime.Logger.Info("start to read embedded init shell: %s", staticembed.SysInitOracleScriptFileName)
	tplBytes, err := staticembed.SysInitOracleScript.ReadFile(staticembed.SysInitOracleScriptFileName)
	if err != nil {
		o.Runtime.Logger.Error("read embedded %s fail, error:%s", staticembed.SysInitOracleScriptFileName, err)
		return fmt.Errorf("read embedded %s fail, error:%s", staticembed.SysInitOracleScriptFileName, err)
	}
	tpl := string(tplBytes)

	o.Runtime.Logger.Info("start to make init script content")
	replacer := strings.NewReplacer(
		"{{user}}", consts.OracleAccount,
		"{{group}}", consts.OracleGroup,
		"{{dba_group}}", consts.DBAGroup,
		"{{password}}", o.Params.Account.Password,
		"{{oracle_sid}}", o.Params.OracleSid,
		"{{cf_ssn}}", o.Params.CfSsn,
		"{{cf_schema}}", o.Params.CfSchema,
	)
	maskedReplacer := strings.NewReplacer(
		"{{user}}", consts.OracleAccount,
		"{{group}}", consts.OracleGroup,
		"{{dba_group}}", consts.DBAGroup,
		"{{password}}", "***REDACTED***",
		"{{oracle_sid}}", o.Params.OracleSid,
		"{{cf_ssn}}", o.Params.CfSsn,
		"{{cf_schema}}", o.Params.CfSchema,
	)
	data := replacer.Replace(tpl)
	dataMasked := maskedReplacer.Replace(tpl)
	o.Runtime.Logger.Info("make init script content successfully")

	o.Runtime.Logger.Info("start to create init script file")
	tmpScriptName := fmt.Sprintf("/tmp/os_oracle_init_%s.sh", time.Now().Format("20060102_150405"))
	if err = os.WriteFile(tmpScriptName, []byte(data), 0755); err != nil {
		o.Runtime.Logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	o.Runtime.Logger.Info("create init script file successfully: %s", tmpScriptName)

	// 无论后续执行成功/失败，都用脱敏版本覆盖回同一个文件
	defer func() {
		if err := os.WriteFile(tmpScriptName, []byte(dataMasked), 0755); err != nil {
			o.Runtime.Logger.Warn("mask password in %s failed: %s", tmpScriptName, err.Error())
		} else {
			o.Runtime.Logger.Info("mask password in %s successfully", tmpScriptName)
		}
	}()

	o.Runtime.Logger.Info("start to execute init script")
	if _, err := util.RunBashCmd(tmpScriptName, "", nil, 60*time.Second); err != nil {
		o.Runtime.Logger.Error("execute init script fail, error:%s (script kept at %s)",
			err, tmpScriptName)
		return fmt.Errorf("execute init script fail, error:%s", err)
	}
	o.Runtime.Logger.Info("execute init script successfully")

	return nil
}

// Retry times
func (o *SysInitCommand) Retry() uint {
	return 2
}

// Rollback rollback
func (o *SysInitCommand) Rollback() error {
	return nil
}
