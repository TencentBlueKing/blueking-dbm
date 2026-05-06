package spider

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/internal/spider"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/mysql"
)

type ImportPrivFileComponent struct {
	mysql.ImportPrivFileComponent
}

func (c *ImportPrivFileComponent) ParseFile() error {
	if !c.Param.IsSpider {
		err := fmt.Errorf("ParseFile called with wrong IsSpider flag, mysql expects IsSpider=false, spider expects IsSpider=true")
		logger.Error(err.Error())
		return err
	}

	//systemUsers := c.Param.SystemUsers
	//if c.Param.SpiderSkipUser != "" {
	//	systemUsers = append(systemUsers, c.Param.SpiderSkipUser)
	//}

	_, err := spider.ParseFile(
		c.ImportPrivFileComponent.SourcePrivFileCpPath(),
		c.ImportPrivFileComponent.SrcVer(),
		c.DstVer(),
		c.Param.SourceIP,
		c.Param.TargetIP,
		c.Param.SystemUsers,
	)
	if err != nil {
		logger.Error("parse spider grants file err: %v", err)
		return err
	}
	return nil
}
