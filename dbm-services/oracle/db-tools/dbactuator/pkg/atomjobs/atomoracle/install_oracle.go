package atomoracle

import (
	"dbm-services/oracle/db-tools/dbactuator/pkg/atomjobs"
	"dbm-services/oracle/db-tools/dbactuator/pkg/common"
	"dbm-services/oracle/db-tools/dbactuator/pkg/consts"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/oracle/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-playground/validator/v10"
)

// InstallOracleParams 执行脚本初始化参数
type InstallOracleParams struct {
	PlainDirs []string                      `json:"plain_dirs"`
	LinkPlans map[string][]SymbolicLinkInfo `json:"link_plans"`
	OraclePkg atomjobs.Medium               `json:"oracle_pkg"`
	PatchList []atomjobs.Medium             `json:"patch_list"`
}

// InstallOracle 执行脚本原子任务   root用户执行
type InstallOracle struct {
	BaseJob
	Params                  *InstallOracleParams
	InstallOracleRunTimeCtx `json:"-"`
}

type InstallOracleRunTimeCtx struct {
	// DirPlan 根据 PlainDirs / LinkPlans 汇总出的分组结构化清单
	DirPlan *DirPlan `json:"dir_plan"`
	// DirScriptPath 目录/软链接准备 shell 脚本的绝对路径（执行完成/失败后均保留，便于排查）
	DirScriptPath string `json:"dir_script_path"`
}

// NewInstallOracle new
func NewInstallOracle() jobruntime.JobRunner {
	return &InstallOracle{}
}

// Init 初始化
func (e *InstallOracle) Init(runtime *jobruntime.JobGenericRuntime) error {
	e.Runtime = runtime
	err := json.Unmarshal([]byte(e.Runtime.PayloadDecoded), &e.Params)
	if err != nil {
		e.Runtime.Logger.Error(
			"get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
		return fmt.Errorf("get parameters of InstallOracle fail by json.Unmarshal, error:%s", err)
	}
	if err = e.checkParams(); err != nil {
		return err
	}
	e.Runtime.Logger.Info("init successfully")
	return nil
}

// checkParams 校验参数
func (e *InstallOracle) checkParams() error {
	// 校验配置参数
	e.Runtime.Logger.Info("start to validate parameters")
	validate := validator.New()
	e.Runtime.Logger.Info("start to validate parameters of InstallOracle")
	if err := validate.Struct(e.Params); err != nil {
		e.Runtime.Logger.Error("validate parameters of InstallOracle fail, error:%s", err)
		return fmt.Errorf("validate parameters of InstallOracle fail, error:%s", err)
	}
	e.Runtime.Logger.Info("validate parameters successfully")
	return nil
}

// Name 名字
func (e *InstallOracle) Name() string {
	return "install"
}

// Run 执行函数
func (e *InstallOracle) Run() error {
	if err := e.PrepareDirs(); err != nil {
		return err
	}
	if err := e.PreCheck(); err != nil {
		return err
	}
	if err := e.extractPackages(); err != nil {
		return err
	}
	if err := e.prepareResponseFile(); err != nil {
		return err
	}
	if err := e.runInstaller(); err != nil {
		return err
	}
	if err := e.checkInstallLog(); err != nil {
		return err
	}
	return nil
}

// PreCheck 预检查
func (e *InstallOracle) PreCheck() error {
	packages := append(append([]atomjobs.Medium{}, e.Params.OraclePkg), e.Params.PatchList...)
	for _, patch := range packages {
		if err := patch.Check(); err != nil {
			e.Runtime.Logger.Error("install package check failed: %s", err.Error())
			return err
		}
	}
	return nil
}

// databaseDir 返回 Oracle 解压后 database 目录的绝对路径
func (e *InstallOracle) databaseDir() string {
	return path.Join(cst.BK_PKG_INSTALL_PATH, "database")
}

// rspRelPath 返回响应文件相对 database 目录的路径
func (e *InstallOracle) rspRelPath() string {
	return path.Join("response", staticembed.DBInstallRSPFileName)
}

// rspPath 返回响应文件的绝对路径
func (e *InstallOracle) rspPath() string {
	return path.Join(e.databaseDir(), e.rspRelPath())
}

// extractPackages 解压 Oracle 安装包及补丁
func (e *InstallOracle) extractPackages() error {
	// 1. 解压 Oracle 软件 tar 包
	if err := e.Params.OraclePkg.Untar(); err != nil {
		e.Runtime.Logger.Error("untar oracle package failed: %s", err.Error())
		return err
	}
	// 2. 解压 tar 包中的分卷 zip 以及补丁 zip
	part1 := fmt.Sprintf("%s_1of7.zip", strings.TrimSuffix(e.Params.OraclePkg.Name, ".tar"))
	part2 := fmt.Sprintf("%s_2of7.zip", strings.TrimSuffix(e.Params.OraclePkg.Name, ".tar"))
	parts := []atomjobs.Medium{
		{Name: part1},
		{Name: part2},
	}
	packages := append(parts, e.Params.PatchList...)
	for _, pkg := range packages {
		e.Runtime.Logger.Info("start to unzip package: %s", pkg)
		if err := pkg.Unzip(); err != nil {
			e.Runtime.Logger.Error("unzip package failed: %s", err.Error())
			return err
		}
		e.Runtime.Logger.Info("unzip package successfully: %s", pkg)
	}
	return nil
}

// prepareResponseFile 释放内嵌的响应文件，并将 ORACLE_HOSTNAME 替换为当前主机名
func (e *InstallOracle) prepareResponseFile() error {
	if err := e.releaseResponseFile(); err != nil {
		return err
	}
	if err := e.setResponseHostname(); err != nil {
		return err
	}
	return nil
}

// releaseResponseFile 将内嵌的 db_install.rsp 释放到 database/response/ 下，覆盖官方模板
func (e *InstallOracle) releaseResponseFile() error {
	rspPath := e.rspPath()

	e.Runtime.Logger.Info("start to release response file to %s", rspPath)
	rspContent, err := staticembed.DBInstallRSP.ReadFile(staticembed.DBInstallRSPFileName)
	if err != nil {
		e.Runtime.Logger.Error("read embedded response file failed: %s", err.Error())
		return fmt.Errorf("read embedded response file failed: %s", err.Error())
	}
	if err = common.CreateFileAndChown(e.Runtime, rspPath, rspContent,
		consts.OracleAccount, consts.OracleGroup, 0644); err != nil {
		return err
	}
	e.Runtime.Logger.Info("release response file successfully")
	return nil
}

// setResponseHostname 修改响应文件里的 ORACLE_HOSTNAME 为当前主机名
func (e *InstallOracle) setResponseHostname() error {
	e.Runtime.Logger.Info("start to set ORACLE_HOSTNAME in response file")
	sedCmd := fmt.Sprintf(`sed -i "s/^ORACLE_HOSTNAME=.*$/ORACLE_HOSTNAME=$(hostname)/" %s`, e.rspPath())
	if _, err := util.RunBashCmd(sedCmd, "", nil, 30*time.Second); err != nil {
		e.Runtime.Logger.Error("sed ORACLE_HOSTNAME failed: %s", err.Error())
		return fmt.Errorf("sed ORACLE_HOSTNAME failed: %s", err.Error())
	}
	e.Runtime.Logger.Info("set ORACLE_HOSTNAME successfully")
	return nil
}

// runInstaller 以 oracle 用户执行 runInstaller 静默安装
func (e *InstallOracle) runInstaller() error {
	e.Runtime.Logger.Info("start to run runInstaller as user %s", consts.OracleAccount)
	databaseDir := e.databaseDir()
	// responseFile 需要填写绝对路径
	installCmd := fmt.Sprintf(
		`su - %s -c "cd %s && ./runInstaller -silent -responseFile %s/%s -ignoreSysPrereqs -showProgress"`,
		consts.OracleAccount, databaseDir, databaseDir, e.rspRelPath(),
	)
	e.Runtime.Logger.Info("installCmd: %s", installCmd)
	if _, err := util.RunBashCmd(installCmd, "", nil, 60*time.Minute); err != nil {
		e.Runtime.Logger.Error("runInstaller failed: %s", err.Error())
		return fmt.Errorf("runInstaller failed: %s", err.Error())
	}
	e.Runtime.Logger.Info("runInstaller finished successfully")
	return nil
}

// checkInstallLog 校验 Oracle 安装日志
func (e *InstallOracle) checkInstallLog() error {
	e.Runtime.Logger.Info("start to check oracle install logs under %s", consts.OraInventoryLogDir)

	// 1. 找最新的 oraInstall*.err
	pattern := filepath.Join(consts.OraInventoryLogDir, "oraInstall*.err")
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return fmt.Errorf("glob %s failed: %s", pattern, err.Error())
	}
	if len(matches) == 0 {
		msg := fmt.Sprintf("no oraInstall*.err found under %s, installation likely did not start",
			consts.OraInventoryLogDir)
		e.Runtime.Logger.Error(msg)
		return fmt.Errorf(msg)
	}

	var latestErr string
	var latestModTime time.Time
	for _, f := range matches {
		fi, statErr := os.Stat(f)
		if statErr != nil {
			e.Runtime.Logger.Warn("stat %s failed: %s", f, statErr.Error())
			continue
		}
		if fi.ModTime().After(latestModTime) {
			latestModTime = fi.ModTime()
			latestErr = f
		}
	}
	if latestErr == "" {
		return fmt.Errorf("no readable oraInstall*.err under %s", consts.OraInventoryLogDir)
	}

	// 2. 从文件名提取 TIMESTAMP
	// oraInstall2026-04-15_04-39-05PM.err → 2026-04-15_04-39-05PM
	base := filepath.Base(latestErr)
	timestamp := strings.TrimSuffix(strings.TrimPrefix(base, "oraInstall"), ".err")
	errFile := latestErr
	outFile := filepath.Join(consts.OraInventoryLogDir, fmt.Sprintf("oraInstall%s.out", timestamp))
	silentFile := filepath.Join(consts.OraInventoryLogDir, fmt.Sprintf("silentInstall%s.log", timestamp))

	e.Runtime.Logger.Info("use log timestamp: %s", timestamp)
	e.Runtime.Logger.Info("  ERR: %s", errFile)
	e.Runtime.Logger.Info("  OUT: %s", outFile)
	e.Runtime.Logger.Info("  SILENT: %s", silentFile)

	var failed bool

	// 3.1 err 必须为空
	errStat, err := os.Stat(errFile)
	if err != nil {
		e.Runtime.Logger.Error("stat err file failed: %s", err.Error())
		failed = true
	} else if errStat.Size() > 0 {
		content, _ := os.ReadFile(errFile)
		e.Runtime.Logger.Error("[1] err log is not empty, content:\n%s", string(content))
		failed = true
	} else {
		e.Runtime.Logger.Info("[1] err log is empty, ok")
	}

	// 3.2 out 必须含两个成功关键字
	outContent, err := os.ReadFile(outFile)
	if err != nil {
		e.Runtime.Logger.Error("read out file failed: %s", err.Error())
		failed = true
	} else if strings.Contains(string(outContent), consts.InstallSuccessKeyword) &&
		strings.Contains(string(outContent), consts.SetupSuccessKeyword) {
		e.Runtime.Logger.Info("[2] out log contains success keywords, ok")
	} else {
		e.Runtime.Logger.Error("[2] out log missing success keywords, tail(%d):\n%s",
			consts.LogTailLines, tailLines(string(outContent), consts.LogTailLines))
		failed = true
	}

	// 3.3 silent 必须含安装成功关键字
	silentContent, err := os.ReadFile(silentFile)
	if err != nil {
		e.Runtime.Logger.Error("read silent file failed: %s", err.Error())
		failed = true
	} else if strings.Contains(string(silentContent), consts.InstallSuccessKeyword) {
		e.Runtime.Logger.Info("[3] silentInstall log contains success keyword, ok")
	} else {
		e.Runtime.Logger.Error("[3] silentInstall log missing success keyword, tail(%d):\n%s",
			consts.LogTailLines, tailLines(string(silentContent), consts.LogTailLines))
		failed = true
	}

	if failed {
		return fmt.Errorf("oracle install log check failed, please see logs above")
	}
	e.Runtime.Logger.Info("oracle install log check passed")
	return nil
}

// tailLines 返回 s 的最后 n 行，用于失败时截断超长日志
func tailLines(s string, n int) string {
	if n <= 0 {
		return ""
	}
	lines := strings.Split(s, "\n")
	if len(lines) <= n {
		return s
	}
	return strings.Join(lines[len(lines)-n:], "\n")
}
