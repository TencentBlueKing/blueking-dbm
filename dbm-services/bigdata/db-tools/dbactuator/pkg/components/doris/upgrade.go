package doris

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// UpgradeParams 升级节点参数
type UpgradeParams struct {
	Host       string `json:"host" validate:"required,ip"`     // 主机IP
	Role       string `json:"role" validate:"required"`        // 角色 eg: follower / hot
	OldVersion string `json:"old_version" validate:"required"` // 旧版本号 eg: 2.1.5
	NewVersion string `json:"new_version" validate:"required"` // 新版本号 eg: 3.0.4
}

// UpgradeService 升级节点Service
type UpgradeService struct {
	GeneralParam    *components.GeneralParam
	Params          *UpgradeParams
	RollBackContext rollback.RollBackObjects
	InstallParams
}

// PreCheck 升级前预检查
func (u *UpgradeService) PreCheck() (err error) {
	roleImp := RoleEnum(u.Params.Role)
	if roleImp == nil {
		return fmt.Errorf("invalid role: %s", u.Params.Role)
	}
	group := roleImp.Group()

	// 检查新版本目录是否存在
	newDorisDir := filepath.Join(u.DorisEnvDir, fmt.Sprintf("doris-%s", u.Params.NewVersion), string(group))
	if _, err := os.Stat(newDorisDir); os.IsNotExist(err) {
		return fmt.Errorf("新版本目录不存在: %s", newDorisDir)
	}

	// 检查新版本JDK是否存在
	newJdkDir := filepath.Join(u.DorisEnvDir, "java", fmt.Sprintf("jdk-doris-%s", u.Params.NewVersion))
	if _, err := os.Stat(newJdkDir); os.IsNotExist(err) {
		return fmt.Errorf("新版本JDK目录不存在: %s", newJdkDir)
	}

	logger.Info("upgrade pre-check passed")
	return nil
}

// StopProcess 停止进程
func (u *UpgradeService) StopProcess() (err error) {
	if err = SupervisorCommand("stop", u.Params.Role); err != nil {
		logger.Error("stop process %s failed, %v", u.Params.Role, err)
		return err
	}
	logger.Info("stop process %s successfully", u.Params.Role)
	return nil
}

// SwitchRoleLink 切换角色软链到新版本（幂等：ln -snf 天然幂等，直接覆盖）
func (u *UpgradeService) SwitchRoleLink() (err error) {
	roleImp := RoleEnum(u.Params.Role)
	if roleImp == nil {
		return fmt.Errorf("invalid role: %s", u.Params.Role)
	}
	group := roleImp.Group()

	// ln -snf 天然幂等，-n 防止将已存在的目录软链当作目录进入
	extraCmd := fmt.Sprintf("cd %s && ln -snf doris-%s/%s %s",
		u.DorisEnvDir, u.Params.NewVersion, group, u.Params.Role)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("switch role symlink failed: %s, %v", extraCmd, err)
		return err
	}

	logger.Info("switch role symlink: %s -> doris-%s/%s", u.Params.Role, u.Params.NewVersion, group)
	return nil
}

// SwitchJdkLink 切换JDK软链到新版本（幂等：只在备份目标不存在时才mv，ln -sf 天然幂等）
func (u *UpgradeService) SwitchJdkLink() (err error) {
	jdkDir := filepath.Join(u.DorisEnvDir, "java")
	jdkPath := filepath.Join(jdkDir, "jdk")
	oldJdkBackup := filepath.Join(jdkDir, fmt.Sprintf("jdk-doris-%s", u.Params.OldVersion))

	// 幂等：只在备份目标不存在且jdk存在时才执行mv
	if _, err := os.Stat(oldJdkBackup); os.IsNotExist(err) {
		// 备份目标不存在，检查jdk是否存在
		if info, err := os.Lstat(jdkPath); err == nil {
			// 区分jdk是真实目录还是软链，方便排查问题
			if info.Mode()&os.ModeSymlink != 0 {
				logger.Info("current jdk at %s is a symlink, will rename to jdk-doris-%s", jdkPath, u.Params.OldVersion)
			} else {
				logger.Info("current jdk at %s is a real directory (first upgrade), will rename to jdk-doris-%s",
					jdkPath, u.Params.OldVersion)
			}
			// jdk存在，执行备份
			mvCmd := fmt.Sprintf("mv %s %s", jdkPath, oldJdkBackup)
			if _, err := osutil.ExecShellCommand(false, mvCmd); err != nil {
				logger.Error("backup old jdk failed: %s, %v", mvCmd, err)
				return err
			}
			logger.Info("backup old jdk: jdk -> jdk-doris-%s", u.Params.OldVersion)
		} else {
			logger.Info("jdk not found at %s, skip backup", jdkPath)
		}
	} else {
		logger.Info("old jdk backup already exists at %s, skip mv", oldJdkBackup)
	}

	// ln -snf 天然幂等，-n 防止将已存在的目录软链当作目录进入
	linkCmd := fmt.Sprintf("cd %s && ln -snf jdk-doris-%s jdk", jdkDir, u.Params.NewVersion)
	if _, err = osutil.ExecShellCommand(false, linkCmd); err != nil {
		logger.Error("switch jdk symlink failed: %s, %v", linkCmd, err)
		return err
	}

	logger.Info("switch jdk symlink: jdk -> jdk-doris-%s", u.Params.NewVersion)
	return nil
}

// ChownNewVersion 对新版本目录和JDK目录赋权给mysql用户（解压时可能以root执行，属主非mysql）
func (u *UpgradeService) ChownNewVersion() (err error) {
	// 对新版本doris目录赋权
	newDorisDir := filepath.Join(u.DorisEnvDir, fmt.Sprintf("doris-%s", u.Params.NewVersion))
	chownDorisCmd := fmt.Sprintf("chown -R %s:root %s", DefaultDorisExecUser, newDorisDir)
	if _, err = osutil.ExecShellCommand(false, chownDorisCmd); err != nil {
		logger.Error("chown new doris dir failed: %s, %v", chownDorisCmd, err)
		return err
	}
	logger.Info("chown new doris dir: %s", newDorisDir)

	// 对新版本JDK目录赋权
	newJdkDir := filepath.Join(u.DorisEnvDir, "java", fmt.Sprintf("jdk-doris-%s", u.Params.NewVersion))
	chownJdkCmd := fmt.Sprintf("chown -R %s:root %s", DefaultDorisExecUser, newJdkDir)
	if _, err = osutil.ExecShellCommand(false, chownJdkCmd); err != nil {
		logger.Error("chown new jdk dir failed: %s, %v", chownJdkCmd, err)
		return err
	}
	logger.Info("chown new jdk dir: %s", newJdkDir)

	return nil
}

// StartProcess 启动进程
func (u *UpgradeService) StartProcess() (err error) {
	if err = SupervisorCommand("start", u.Params.Role); err != nil {
		logger.Error("start process %s failed, %v", u.Params.Role, err)
		return err
	}
	logger.Info("start process %s successfully", u.Params.Role)
	return nil
}

// CheckComponentRunning 校验当前角色在 supervisor 中已 RUNNING（5s × 3 次轮询）。
// 用于 upgrade_node 的启动后活性检查。
func (u *UpgradeService) CheckComponentRunning() error {
	return dorisutil.CheckComponentRunning(u.Params.Role)
}
