package doris

import (
	"database/sql"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/common/go-pubpkg/logger"
	"errors"
	"fmt"

	_ "github.com/go-sql-driver/mysql" // mysql
)

// UpdateMetaDataService TODO
type UpdateMetaDataService struct {
	GeneralParam *components.GeneralParam
	Params       *UpdateMetadataParams
	InstallParams
	RollBackContext rollback.RollBackObjects
}

// UpdateMetadataParams 更新Metadata 参数 结构体
type UpdateMetadataParams struct {
	Host         string              `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort    int                 `json:"query_port" validate:"required"`
	UserName     string              `json:"username" validate:"required"`
	Password     string              `json:"password" validate:"required"`
	RootPassword string              `json:"root_password"`
	Operation    MetaOperation       `json:"operation" validate:"required"`
	HostMap      map[string][]string `json:"host_map" validate:"required"`
}

// UpdateMetaDataInternal 更新metadata 内部方法
func (i *UpdateMetaDataService) UpdateMetaDataInternal() (failHostMap map[string][]string, failErr error) {

	rootPwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		i.Params.UserName, rootPwd, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		failHostMap = i.Params.HostMap
		return failHostMap, err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)

	failHostMap = make(map[string][]string)
	for role, hosts := range i.Params.HostMap {

		roleEnum := RoleEnum(role)
		var metaRole string
		if roleEnum.Value() == Hot || roleEnum.Value() == Cold || roleEnum.Value() == Warm {
			metaRole = "BACKEND"
		} else {
			metaRole = role
		}
		for _, host := range hosts {
			if host == i.Params.Host {
				// 若元数据更新的IP为操作IP，跳过不执行
				logger.Info("params host now is %s, same as operation host, skip", host)
				continue
			}
			metaDataSql := fmt.Sprintf("ALTER SYSTEM %s %s '%s:%d'", i.Params.Operation,
				metaRole, host, roleEnum.InnerPort())
			// 执行SQL
			_, err = db.Exec(metaDataSql)
			if err != nil {
				failErr = err
				value, ok := failHostMap[role]
				if ok {
					value = append(value, host)
				} else {
					value = []string{host}
				}
				failHostMap[role] = value
			}
		}
	}
	return failHostMap, failErr
}

// UpdateMetaData 更新Metadata
func (i *UpdateMetaDataService) UpdateMetaData() (err error) {
	failHostMap, err := i.UpdateMetaDataInternal()
	if err != nil {
		logger.Error("更新集群节点元数据失败, %v", failHostMap)
		return err
	} else {
		return
	}
}

// UpdateBackendsTag 更新 BE节点所属Tag类型
func (i *UpdateMetaDataService) UpdateBackendsTag(tag string, backendIps []string) (err error) {

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		i.Params.UserName, i.Params.Password, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	// 统计更新失败的IP列表
	var failedIps []string
	// 遍历执行SQL，不封装为单个IP执行，减少额外的DB连接(其实可以将DB连接包做一个变量，退出时再释放)
	for _, ip := range backendIps {
		updateTagSql := fmt.Sprintf("ALTER SYSTEM MODIFY BACKEND \"%s:%d\" set (\"tag.location\" = \"%s\");",
			ip, BeHeartBeatPort, tag)
		// 执行SQL
		_, err = db.Exec(updateTagSql)
		if err != nil {
			logger.Error("update backend ip %s tag failed. err: %s", ip, err.Error())
			failedIps = append(failedIps, ip)
		}
	}
	if len(failedIps) > 0 {
		return errors.New(fmt.Sprintf("update backends tag failed, need to fix manualy, failedIps is %v", failedIps))
	} else {
		return nil
	}
}
