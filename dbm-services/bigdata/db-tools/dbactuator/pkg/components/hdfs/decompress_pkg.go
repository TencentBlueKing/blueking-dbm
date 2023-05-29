package hdfs

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// DecompressPkgParams TODO
type DecompressPkgParams struct {
	HdfsSite      map[string]string `json:"hdfs-site"`
	CoreSite      map[string]string `json:"core-site"`
	ZooCfg        map[string]string `json:"zoo.cfg"`
	InstallConfig `json:"install"`
	Version       string `json:"version"  validate:"required"` // 版本号eg: 2.6.0-cdh-5.4.11

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
	if err = os.Chdir(i.InstallDir); err != nil {
		return fmt.Errorf("cd to dir %s failed, err:%w", i.InstallDir, err)
	}
	// 判断 Hadoop Home 目录是否已经存在,如果存在则删除掉
	if util.FileExists(i.HdfsHomeDir) {
		if _, err = osutil.ExecShellCommand(false, "rm -rf "+i.HdfsHomeDir); err != nil {
			logger.Error("rm -rf %s error: %w", i.HdfsHomeDir, err)
			return err
		}
	}
	return nil
}

// DecompressPkg TODO
func (i *DecompressPkgService) DecompressPkg() (err error) {
	// 压缩包中包含jdk, hadoop, supervisor, telegraf, haproxy
	pkgAbPath := i.PkgDir + "/hdfspack-" + i.Params.Version + ".tar.gz"
	if output, err := osutil.ExecShellCommand(false, fmt.Sprintf("tar zxf %s -C %s", pkgAbPath,
		i.InstallDir)); err != nil {
		logger.Error("tar zxf %s error:%s,%s", pkgAbPath, output, err.Error())
		return err
	}

	// 配置hadoop软链
	extraCmd := fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/hadoop-"+i.Params.Version, i.HdfsHomeDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	// 配置JDK软链
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/"+i.JdkVersion, i.JdkDir)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	// 配置ZK软链
	extraCmd = fmt.Sprintf("ln -sf %s %s", i.InstallDir+"/zookeeper-"+i.ZkVersion, "zookeeper")
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("%s execute failed, %v", extraCmd, err)
		return err
	}
	logger.Info("decompress hdfs pkg successfully")
	return nil
}
