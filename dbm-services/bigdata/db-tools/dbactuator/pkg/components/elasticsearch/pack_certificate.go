package elasticsearch

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/hashicorp/go-version"
)

// PackCerComp struct
type PackCerComp struct {
	GeneralParam    *components.GeneralParam
	Params          *PackCerParams
	RollBackContext rollback.RollBackObjects
}

// PackCerParams param
type PackCerParams struct {
	EsVersion string `json:"es_version"`
}

// Init function
func (d *PackCerComp) Init() (err error) {
	logger.Info("Generate certificate fake init")
	return nil
}

// PackCer 710 for pack es certificate files
// Usage: dbactuator es pack_certificate xxxxxx
// For 7.10.2, copy key files and elasticsearch.yml.append  to  /tmp/
// For 7.14.2, copy key files and elasticsearch.yml.append  to  /tmp/
// Finally, it will output the tar.gz package in /tmp, named es_cerfiles.tar.gz
// And the transfer files to other nodes
func (d *PackCerComp) PackCer() (err error) {
	v, _ := version.NewVersion(d.Params.EsVersion)
	v7, _ := version.NewVersion(cst.ES7142)
	cerFiles := cst.CerFile
	if v.LessThan(v7) {
		cerFiles = cst.CerFile710
	}
	confDir := cst.DefaulEsConfigDir
	if err := TarCerFiles(confDir, cerFiles); err != nil {
		logger.Error("package cerfiles failed, msg [%s]", err)
		return err
	}

	return nil
}

// TarCerFiles TODO
func TarCerFiles(dir string, cerFiles []string) error {
	// First, change dir to /tmp
	if err := os.Chdir("/tmp"); err != nil {
		logger.Error("Change dir to [tmp] failed %s", err)
		return err
	}

	// For rerunable, delete ca files first
	extraCmd := "rm -rf /tmp/{es_cerfiles.tar.gz,es_cerfiles}"
	logger.Info("Delete certificate file/dir first,[%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// Create es_cerfiles dir
	esCerDir := "/tmp/es_cerfiles"
	extraCmd = fmt.Sprintf("mkdir -p %s", esCerDir)
	logger.Info("Make dir, exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// Copy key files and elasticsearch.yml.append file to /tmp/es_cerfiles
	for _, f := range cerFiles {
		// cp /data/esenv/es_1/config/xxx /tmp/es_cerfiles/
		extraCmd = fmt.Sprintf("cp %s/%s %s", dir, f, esCerDir)
		logger.Info("Exec [%s]", extraCmd)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
			return err
		}
	}

	// In tmp dir, Tar es_cerfiles
	extraCmd = "tar zcf es_cerfiles.tar.gz es_cerfiles"
	logger.Info("Tar dir [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	return nil
}
