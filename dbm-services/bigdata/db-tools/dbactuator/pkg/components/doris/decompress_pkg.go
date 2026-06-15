package doris

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// 原地升级场景下，从 dorispack-{version}.tar.gz 中抽取 JDK 子目录的解压参数。
//
// 压缩包内 JDK 的目录结构为 java/jdk/<jdk 内容>，原地升级时希望将 <jdk 内容>
// 直接解压到 newVersionJdkAbsPath（即 /data/dorisenv/java/jdk-doris-{version}）下，
// 因此需要：
//  1. 用 jdkArchiveSubPath 限定只解 JDK 子目录，避免把整包内容解出来；
//  2. 用 jdkArchiveStripDepth 把 jdkArchiveSubPath 自身的层级剥掉。
//
// 二者必须同步修改：jdkArchiveStripDepth == strings.Count(jdkArchiveSubPath, "/") + 1。
const (
	jdkArchiveSubPath    = "java/jdk"
	jdkArchiveStripDepth = 2
)

// DecompressPkgParams 解压参数
//
// OperationType 字段说明：
//   - 含义：操作类型，传参为单据类型(如 DORIS_APPLY / DORIS_SCALE_UP / DORIS_UPGRADE)。
//   - 校验：选传字段，使用 validate:"omitempty"。未传或为空时，按存量行为处理（即 V1 的部署/扩缩容逻辑）；
//     仅当显式传入 DORIS_UPGRADE 时，会走升级专属分支（如 V2 解压不切换软链等）。
type DecompressPkgParams struct {
	Version       string `json:"version" validate:"required"`         // 版本号eg: 2.0.1
	Role          string `json:"role" validate:"required"`            // 角色 eg: follower / hot
	OperationType string `json:"operation_type" validate:"omitempty"` // 操作类型，详见结构体注释
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
	pkgAbPath := filepath.Join(i.PkgDir, fmt.Sprintf("dorispack-%s.tar.gz", i.Params.Version))
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s -C %s", pkgAbPath,
		i.DorisEnvDir)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}
	group := RoleEnum(i.Params.Role).Group()
	// 配置doris软链，-n 防止将已存在的目录软链当作目录进入
	extraCmd := fmt.Sprintf("cd %s ; ln -snf doris-%s/%s %s",
		i.DorisEnvDir, i.Params.Version, group, i.Params.Role)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}

	logger.Info("decompress doris pkg successfully")
	return nil
}

// DecompressDorisPkgV2 v2版本解压缩，兼容扩容节点及原地升级两种场景
func (i *DecompressPkgService) DecompressDorisPkgV2() (err error) {
	// 压缩包中包含jdk, doris, supervisor
	// 当操作类型为upgrade时，不进行角色和安装包目录的软链

	if i.Params.OperationType != Upgrade {
		return i.DecompressDorisPkg()
	}
	// 封装原地升级新版本压缩包路径
	pkgAbPath := filepath.Join(i.PkgDir, fmt.Sprintf("dorispack-%s.tar.gz", i.Params.Version))
	// 1. 压缩包 内置doris-{version}目录, 直接到Doris服务目录，不会与旧版本冲突
	extractDorisCmd := fmt.Sprintf("tar zxf %s -C %s doris-%s", pkgAbPath, i.DorisEnvDir, i.Params.Version)
	if output, err := osutil.ExecShellCommand(false, extractDorisCmd); err != nil {
		logger.Error("extractDorisCmd: %s error:%s,%s", extractDorisCmd, output, err.Error())
		return err
	}
	// 2. 压缩包 内置未指定JDK对应doris版本目录, 处理方式不同于扩容节点
	// 定义新版本的JDK绝对路径，保持JAVA_HOME为/data/dorisenv/java/jdk不变，后续升级时使用软链
	newVersionJdkAbsPath := filepath.Join(i.DorisEnvDir, fmt.Sprintf("java/jdk-doris-%s", i.Params.Version))
	mkdirCmd := fmt.Sprintf("mkdir -p %s", newVersionJdkAbsPath)
	if output, err := osutil.ExecShellCommand(false, mkdirCmd); err != nil {
		logger.Error("mkdir %s error:%s,%s", newVersionJdkAbsPath, output, err.Error())
		return err
	}
	extractJavaCmd := fmt.Sprintf("tar zxf %s -C %s --strip-components=%d %s",
		pkgAbPath, newVersionJdkAbsPath, jdkArchiveStripDepth, jdkArchiveSubPath)
	if output, err := osutil.ExecShellCommand(false, extractJavaCmd); err != nil {
		logger.Error("extractJavaCmd: %s error:%s,%s", extractJavaCmd, output, err.Error())
		return err
	}

	logger.Info("decompress doris pkg v2 successfully")
	return nil
}
