package elasticsearch

import (
	"fmt"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ReplaceEsNodeComp TODO
type ReplaceEsNodeComp struct {
	GeneralParam    *components.GeneralParam
	Params          *ReplaceEsNodeParams
	RollBackContext rollback.RollBackObjects
}

// ReplaceEsNodeParams TODO
type ReplaceEsNodeParams struct {
	Masters []string `json:"masters"` //
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (r *ReplaceEsNodeComp) Init() (err error) {
	logger.Info("Reduce es node fake init")
	return nil
}

// ReplaceMasterNode TODO
/**
 *  @description: 更新master
 *  @return
 */
func (r *ReplaceEsNodeComp) ReplaceMasterNode() (err error) {
	masters := r.Params.Masters
	ipStr := strings.Join(masters[:], ",")
	masterStr := esutil.ToMasterStr(masters)
	seedHosts := fmt.Sprintf("[%s]", ipStr)
	initMaster := fmt.Sprintf("[%s]", masterStr)
	esenv := cst.DefaulEsEnv
	yamlPaths := fmt.Sprintf(`%s/es_*/config/elasticsearch.yml`, esenv)

	extraCmd := fmt.Sprintf(
		`sed -i -e '/discovery.seed_hosts/s/\[.*\]/%s/' -e '/cluster.initial_master_nodes/s/\[.*\]/%s/' %s`, seedHosts,
		initMaster, yamlPaths)
	logger.Info("更新master, [%s]", extraCmd)
	if _, err = osutil.ExecShellCommand(false, extraCmd); err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return err
	}

	return nil
}
