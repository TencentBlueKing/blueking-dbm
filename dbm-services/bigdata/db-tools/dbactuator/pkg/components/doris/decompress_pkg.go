package doris

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// DecompressPkgParams TODO
type DecompressPkgParams struct {
	Version string `json:"version" validate:"required"` // 版本号eg: 2.0.1
	Role    string `json:"role" validate:"required"`    //
	//Group   string `json:"group" validate:"required"`   // 角色 eg: fe / be
}

// DecompressPkgService TODO
type DecompressPkgService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params *DecompressPkgParams

	RollBackContext rollback.RollBackObjects
}

// PreCheck TODO
func (i *DecompressPkgService) PreCheck() (err error) {

	// 检查解压目标目录是否已创建
	if err = os.Chdir(i.DorisEnvDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.DorisEnvDir, err)
	}
	return nil
}

// DecompressDorisPkg TODO
func (i *DecompressPkgService) DecompressDorisPkg() (err error) {
	// 压缩包中包含jdk, doris, supervisor
	pkgAbPath := i.PkgDir + "/dorispack-" + i.Params.Version + ".tar.gz"
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s -C %s", pkgAbPath,
		i.DorisEnvDir)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	group := RoleEnum(i.Params.Role).Group()
	// 配置doris软链
	extraCmd := fmt.Sprintf("cd %s ; ln -sf doris-%s/%s %s",
		i.DorisEnvDir, i.Params.Version, group, i.Params.Role)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("decompress doris pkg successfully")
	return nil
}
