package elasticsearch

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
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

// Init func
func (d *PackCerComp) Init() (err error) {
	logger.Info("Generate certificate fake init")
	return nil

}

// PackCer 710 for pack es certificate files
func (d *PackCerComp) PackCer() (err error) {
	cerFiles := cst.CerFile
	if d.Params.EsVersion == cst.ES7102 {
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
	if err := os.Chdir("/tmp"); err != nil {
		logger.Error("Change dir to [tmp] failed %s", err)
		return err
	}

	// For rerunable, delete ca file first
	extraCmd := "rm -rf /tmp/{es_cerfiles.tar.gz,es_cerfiles}"
	logger.Info("Delete certificate file/dir first,[%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// Create dir
	esCerDir := "/tmp/es_cerfiles"
	extraCmd = fmt.Sprintf("mkdir -p %s", esCerDir)
	logger.Info("Make dir, exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	for _, f := range cerFiles {
		// cp /data/esenv/es_1/config/xxx /tmp/es_cerfiles/
		extraCmd = fmt.Sprintf("cp %s/%s %s", dir, f, esCerDir)
		logger.Info("Exec [%s]", extraCmd)
		if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
			logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
			return err
		}
	}

	// Tar dir
	extraCmd = "tar zcf es_cerfiles.tar.gz es_cerfiles"
	logger.Info("Tar dir [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	return nil
}
