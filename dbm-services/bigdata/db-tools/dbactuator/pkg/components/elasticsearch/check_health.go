package elasticsearch

import (
	"fmt"
	"os"
	"strconv"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/esutil"
	"dbm-services/common/go-pubpkg/logger"
)

// CheckEsHealthComp TODO
type CheckEsHealthComp struct {
	GeneralParam    *components.GeneralParam
	Params          *CheckEsHealthParams
	RollBackContext rollback.RollBackObjects
}

// CheckEsHealthParams TODO
type CheckEsHealthParams struct {
}

// Init TODO
/**
 *  @description:
 *  @return
 */
func (d *CheckEsHealthComp) Init() (err error) {
	logger.Info("Reduce es node fake init")
	return nil
}

// CheckEsHealth TODO
func (d *CheckEsHealthComp) CheckEsHealth() (err error) {
	username := os.Getenv("ES_USERNAME")
	password := os.Getenv("ES_PASSWORD")
	localIP, err := esutil.GetEsLocalIp()
	if err != nil {
		logger.Error("get local ip failed, %s", err)
		return err
	}
	ports, err := esutil.GetEsLocalPorts()
	if err != nil {
		logger.Error("get ports failed, %s", err)
		return err
	}

	// 检查端口
	var errors string
	for _, port := range ports {
		iPort, _ := strconv.Atoi(port)
		e := esutil.EsInsObject{
			Host:     localIP,
			HttpPort: iPort,
			UserName: username,
			Password: password,
		}
		err = e.CheckEsHealth()
		errors += err.Error()
	}
	if len(errors) != 0 {
		logger.Error("节点可能挂掉了, %s", errors)
		return fmt.Errorf("节点挂了，请检查[%s]", errors)
	}

	logger.Info("节点检查健康")

	return nil
}
