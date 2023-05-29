package elasticsearch

import (
	"fmt"
	"os"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/hashicorp/go-version"
)

// GenCerComp struct
type GenCerComp struct {
	GeneralParam    *components.GeneralParam
	Params          *GenCerParams
	RollBackContext rollback.RollBackObjects
}

// GenCerParams param
type GenCerParams struct {
	EsVersion string `json:"es_version"`
}

// Init func
func (d *GenCerComp) Init() (err error) {
	logger.Info("Generate certificate fake init")
	return nil
}

// GenCer 生成证书
func (d *GenCerComp) GenCer() (err error) {
	ver := d.Params.EsVersion
	v, _ := version.NewVersion(ver)
	v7, _ := version.NewVersion(cst.ES7142)
	switch {
	// version less than 7.14.2,use searchguard or opensecurity
	case v.LessThan(v7):
		logger.Info("Generating sg/opens certificate..")
		if err := d.GenCer710(); err != nil {
			logger.Error("Generate sg/opens certificate filaed, %s", err)
			return err
		}
	default:
		// version >= 7.14.2,use xpack
		logger.Info("Generating  certificate..")
		if err := d.GenCer7(); err != nil {
			logger.Error("Generate certificate filaed, %s", err)
			return err
		}
	}

	return nil
}

// GenCer7 xpack certificate
func (d *GenCerComp) GenCer7() (err error) {
	version := d.Params.EsVersion
	// change dir to /data/install
	if err := os.Chdir(cst.DefaultPkgDir); err != nil {
		logger.Error("Change dir to [/data/install] failed %s", err)
		return err
	}

	esPackName := fmt.Sprintf("espack-%s", version)
	esPkgName := fmt.Sprintf("elasticsearch-%s", version)
	// delete first
	extraCmd := fmt.Sprintf("rm -rf %s; tar zxf %s.tar.gz", esPkgName, esPackName)
	logger.Info("Decompress package, Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// change dir to /data/install/elasticsearch-7.10.1
	tmpEsDir := fmt.Sprintf("%s/elasticsearch-%s", cst.DefaultPkgDir, version)
	if err := os.Chdir(tmpEsDir); err != nil {
		logger.Error("Change dir to [/data/install/elasticsearch-7.x.x] failed %s", err)
		return err
	}

	esTool := fmt.Sprintf("ES_JAVA_HOME=%s/jdk/ bin/elasticsearch-certutil", tmpEsDir)
	// ./bin/elasticsearch-certutil ca
	extraCmd = fmt.Sprintf("%s ca  --days 365000 --out elastic-stack-ca.p12 --pass ''", esTool)
	logger.Info("Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// ./bin/elasticsearch-certutil cert --ca elastic-stack-ca.p12
	extraCmd = fmt.Sprintf(
		"%s cert --ca elastic-stack-ca.p12 --days 365000  --ca-pass '' --pass ''  --out elastic-certificates.p12", esTool)
	logger.Info("Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// elasticsearch.ym.append
	if err := esutil.WriteCerToYaml7(cst.ESYmlAppend); err != nil {
		logger.Error("Write elasticsearch.yml.append failed, msg %s", err)
		return err
	}

	// generate random password
	extraCmd = "< /dev/urandom tr -dc A-Za-z0-9 | head -c8 > es_passfile"
	logger.Info("Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// generate keystore file, elasticsearch-7.14.2/config/elasticsearch.keystore
	extraCmd = fmt.Sprintf(
		`cat es_passfile |ES_JAVA_HOME=%s/jdk/  ./bin/elasticsearch-keystore add -x "bootstrap.password" -f`, tmpEsDir)
	logger.Info("Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// copy elasticsearch-7.14.2/config/elasticsearch.keystore to ../
	extraCmd = "cp config/elasticsearch.keystore ."
	logger.Info("Exec [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// copy file to tmp
	if err := TarCerFiles(tmpEsDir, cst.CerFile); err != nil {
		logger.Error("copy cerFile failed, msg %s", err)
		return err
	}

	return nil
}

// GenCer710 searchgaurd/opensecurity
func (d *GenCerComp) GenCer710() (err error) {
	v, _ := version.NewVersion(d.Params.EsVersion)
	v7, _ := version.NewVersion("7.0")

	if err := os.Chdir(cst.DefaultPkgDir); err != nil {
		logger.Error("Change dir to [tmp] failed %s", err)
		return err
	}

	// For rerunable, delete ca file first

	// check openssl file
	extraCmd := "openssl version"
	logger.Info("Checking openssl command, exec cmd [%s] ...", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// Generate root-ca
	extraCmd = `openssl genrsa -out root-ca-key.pem 2048 ;
		openssl req -new -x509 -sha256 -key root-ca-key.pem -out root-ca.pem -days 36500 \
-subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=root"`
	logger.Info("Generate root-ca, exec cmd [%s]", extraCmd)
	_, _ = osutil.ExecShellCommand(false, extraCmd)

	// admin certificate
	extraCmd = `openssl genrsa -out admin-key-temp.pem 2048 ;
		openssl pkcs8 -inform PEM -outform PEM -in admin-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out admin-key.pem;
		openssl req -new -key admin-key.pem -out admin.csr   -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=admin";
		openssl x509 -req -in admin.csr -CA root-ca.pem -CAkey \
root-ca-key.pem -CAcreateserial -sha256 -out admin.pem -days 36500`
	logger.Info("Generate admin certificate, exec cmd [%s]", extraCmd)
	_, _ = osutil.ExecShellCommand(false, extraCmd)

	// node certificate
	extraCmd = `openssl genrsa -out node-key-temp.pem 2048 ;
		openssl pkcs8 -inform PEM -outform PEM -in node-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out node-key.pem;
		openssl req -new -key node-key.pem -out node.csr  -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=node";
		openssl x509 -req -in node.csr -CA root-ca.pem -CAkey \
root-ca-key.pem -CAcreateserial -sha256 -out node.pem -days 36500`
	logger.Info("Generate node certificate, exec cmd [%s]", extraCmd)
	_, _ = osutil.ExecShellCommand(false, extraCmd)

	// For Compatibility, copy the file
	extraCmd = `cp -a node.pem node1.pem; cp -a node-key.pem node1.key;
	cp -a node.pem node1_http.pem; cp -a node-key.pem node1_http.key;`
	logger.Info("Copy cetificate file to old name, exec cmd [%s]", extraCmd)
	if output, err := osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("cmd [%s] failed, error message: [%s], error code: [%s]", extraCmd, output, err)
		return err
	}

	// Check file Todo, admin.pem  admin-key.pem  root-ca.pem  node.pem  node-key.pem
	// elasticsearch.ym.append
	if v.GreaterThan(v7) {
		if err := esutil.WriteCerToYaml710(cst.ESYmlAppend); err != nil {
			logger.Error("Write elasticsearch.yml.append failed, msg %s", err)
			return err
		}
	} else {
		if err := esutil.WriteCerToYamlSG(cst.ESYmlAppend); err != nil {
			logger.Error("Write elasticsearch.yml.append failed, msg %s", err)
			return err
		}
	}

	// copy file to tmp
	if err := TarCerFiles(cst.DefaultPkgDir, cst.CerFile710); err != nil {
		logger.Error("copy cerFile failed, msg %s", err)
		return err
	}

	return nil
}
