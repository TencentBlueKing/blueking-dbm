package hdfs

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
)

// UpdateHostMappingParams TODO
type UpdateHostMappingParams struct {
	HostMap map[string]string `json:"host_map"`
}

// UpdateHostMappingService TODO
type UpdateHostMappingService struct {
	GeneralParam *components.GeneralParam
	Params       *UpdateHostMappingParams

	RollBackContext rollback.RollBackObjects
}

// UpdateHostMapping TODO
func (i *UpdateHostMappingService) UpdateHostMapping() (err error) {

	for k, v := range i.Params.HostMap {
		deleteCommand := fmt.Sprintf("sed -i '/%s$/d' /etc/hosts", v)
		if _, err := osutil.ExecShellCommand(false, deleteCommand); err != nil {
			logger.Error("exec delete hostname failed %s", err.Error())
		}
		echoCommand := fmt.Sprintf("echo \"%s %s\" >> /etc/hosts", k, v)
		_, err = osutil.ExecShellCommand(false, echoCommand)
		if err != nil {
			logger.Error("exec update host failed %s", err.Error())
		}
	}
	updateCommand := "nscd -i hosts"
	_, err = osutil.ExecShellCommand(false, updateCommand)
	if err != nil {
		logger.Error("nscd host failed %s", err.Error())
	}
	return nil
}
