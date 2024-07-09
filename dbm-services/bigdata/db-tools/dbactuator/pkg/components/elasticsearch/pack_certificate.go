package elasticsearch

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/hashicorp/go-version"
)

// PackCerComp 结构体定义了打包证书组件的参数和回滚上下文
type PackCerComp struct {
	GeneralParam    *components.GeneralParam
	Params          *PackCerParams
	RollBackContext rollback.RollBackObjects
}

// PackCerParams 结构体定义了打包证书组件的参数
type PackCerParams struct {
	EsVersion string `json:"es_version"`
}

// Init 初始化函数，当前仅用于日志记录
func (d *PackCerComp) Init() (err error) {
	logger.Info("Generate certificate fake init")
	return nil
}

// PackCer 函数用于打包 Elasticsearch 证书文件
// Usage: dbactuator es pack_certificate xxxxxx
// For 7.10.2, copy key files and elasticsearch.yml.append  to  /tmp/
// For 7.14.2, copy key files and elasticsearch.yml.append  to  /tmp/
// Finally, it will output the tar.gz package in /tmp, named es_cerfiles.tar.gz
// And the transfer files to other nodes
func (d *PackCerComp) PackCer() (err error) {
	// 解析 Elasticsearch 版本
	v, _ := version.NewVersion(d.Params.EsVersion)
	v7, _ := version.NewVersion(cst.ES7142)
	cerFiles := cst.CerFile
	// 根据版本选择不同的证书文件
	if v.LessThan(v7) {
		cerFiles = cst.CerFile710
	}
	confDir := cst.DefaulEsConfigDir
	// 打包证书文件
	if err := TarCerFiles(confDir, cerFiles); err != nil {
		logger.Error("package cerfiles failed, msg [%s]", err)
		return err
	}

	return nil
}

// TarCerFiles 函数用于打包证书文件
func TarCerFiles(dir string, cerFiles []string) error {
	// 首先，切换到 /tmp 目录
	if err := os.Chdir("/tmp"); err != nil {
		logger.Error("Change dir to [tmp] failed %s", err)
		return err
	}

	// 为了可重入性，先删除旧的证书文件
	extraCmd := "rm -rf /tmp/{es_cerfiles.tar.gz,es_cerfiles}"
	logger.Info("Delete certificate file/dir first,[%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// 创建 es_cerfiles 目录
	esCerDir := "/tmp/es_cerfiles"
	extraCmd = fmt.Sprintf("mkdir -p %s", esCerDir)
	logger.Info("Make dir, exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// 复制密钥文件和 elasticsearch.yml.append 文件到 /tmp/es_cerfiles
	for _, f := range cerFiles {
		// cp /data/esenv/es_1/config/xxx /tmp/es_cerfiles/
		extraCmd = fmt.Sprintf("cp %s/%s %s", dir, f, esCerDir)
		logger.Info("Exec [%s]", extraCmd)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
			return err
		}
	}

	// 复制 ik 或其他文件
	for _, f := range cst.OtherESFiles {
		ff := fmt.Sprintf("%s/%s", dir, f)
		logger.Info(ff)
		// 检查文件是否存在
		if util.FileExists(ff) {
			extraCmd = fmt.Sprintf("cp -r %s %s", ff, esCerDir)
			logger.Info("Exec [%s]", extraCmd)
			if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
				logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
				return err
			}
		}
	}

	// 在 /tmp 目录下打包 es_cerfiles
	extraCmd = "tar zcf es_cerfiles.tar.gz es_cerfiles"
	logger.Info("Tar dir [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	return nil
}
