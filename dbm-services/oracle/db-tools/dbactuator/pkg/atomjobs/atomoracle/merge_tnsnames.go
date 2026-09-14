package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// MergeTnsnamesParams 执行脚本初始化参数
type MergeTnsnamesParams struct {
	TnsnamesFile string `json:"tnsnames_file" validate:"required"`
	MasterHost   string `json:"master_host" validate:"required"`
	SlaveHost    string `json:"slave_host" validate:"required"`
}

// MergeTnsnames 执行脚本原子任务   oracle用户执行
type MergeTnsnames struct {
	BaseJob
	Params                  *MergeTnsnamesParams
	MergeTnsnamesRunTimeCtx `json:"-"`
}

// MergeTnsnamesRunTimeCtx 运行时上下文
type MergeTnsnamesRunTimeCtx struct {
}

// NewMergeTnsnames new
func NewMergeTnsnames() jobruntime.JobRunner {
	return &MergeTnsnames{}
}

// Init 初始化
func (e *MergeTnsnames) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of MergeTnsnames fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of MergeTnsnames fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *MergeTnsnames) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of MergeTnsnames")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of MergeTnsnames fail, error:%s", err)
		return fmt.Errorf("validate parameters of MergeTnsnames fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *MergeTnsnames) Name() string {
	return "merge-tnsnames"
}

// Run 执行函数
func (e *MergeTnsnames) Run() error {
	e.Runtime.Logger.Info("start to merge tnsnames")
	oracleHome := os.Getenv("ORACLE_HOME")
	if oracleHome == "" {
		oracleHome = consts.DefaultOracleHome
	}
	target := oracleHome + "/network/admin/" + staticembed.TnsNamesFileName
	source := e.Params.TnsnamesFile

	if _, err := os.Stat(source); os.IsNotExist(err) {
		e.Runtime.Logger.Error("source file %s not found", source)
		return fmt.Errorf("source file %s not found", source)
	}

	err := MergeTnsnamesFile(source, target)
	if err != nil {
		e.Runtime.Logger.Error("merge tnsnames fail: %s", err)
		return err
	}
	e.Runtime.Logger.Info("merge tnsnames success")

	err = ReplaceLocalIP(target, e.Params.MasterHost, e.Params.SlaveHost)
	if err != nil {
		e.Runtime.Logger.Error("replace local ip fail: %s", err)
		return err
	}
	e.Runtime.Logger.Info("replace local ip success")
	return nil
}

// MergeTnsnamesFile 合并tnsnames.ora文件
func MergeTnsnamesFile(source string, target string) error {
	cmd := fmt.Sprintf("cp -p %s %s.bak.$(date +%%Y%%m%%d%%H%%M%%S)\n", target, target)
	_, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return fmt.Errorf("%s error:%s", cmd, err)
	}
	sourceTns, err := os.ReadFile(source)
	if err != nil {
		return fmt.Errorf("read %s fail, error:%s", source, err)
	}
	f, err := os.OpenFile(target, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("open %s fail, error:%s", target, err)
	}
	defer f.Close()
	if _, err = f.WriteString("\n" + string(sourceTns) + "\n"); err != nil {
		return fmt.Errorf("append content to %s fail, error:%s", target, err)
	}
	return nil
}

// ReplaceLocalIP 替换以 LOCALDB 开头的 TNS 条目内的 IP。
// 匹配时限定 IP 边界：左侧必须是空格或 '='，右侧必须是空格或 ')'
func ReplaceLocalIP(tnsFile string, sourceIp string, targetIp string) error {
	cmd := fmt.Sprintf("cp -p %s %s.bak.$(date +%%Y%%m%%d%%H%%M%%S)\n", tnsFile, tnsFile)
	_, err := util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return fmt.Errorf("%s error:%s", cmd, err)
	}
	// 将 IP 中的 '.' 转义为 '\.'，作为 awk 正则使用
	escapedSrc := strings.ReplaceAll(sourceIp, ".", `\.`)
	cmd = fmt.Sprintf(
		`awk -v t=%q 'BEGIN{RS="";ORS="\n\n"} /^LOCALDB/{$0=gensub(/([ =])%s([ )])/, "\\1" t "\\2", "g")} {print}' %s > %s.tmp && mv %s.tmp %s`,
		targetIp, escapedSrc, tnsFile, tnsFile, tnsFile, tnsFile,
	)
	_, err = util.RunBashCmd(cmd, "", nil, 60*time.Second)
	if err != nil {
		return fmt.Errorf("%s error:%s", cmd, err)
	}
	return nil
}
