package doris

import (
	"database/sql"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/base64"
	"fmt"

	_ "github.com/go-sql-driver/mysql" // mysql
)

// CreateResourceService 创建Doris集群资源接口
type CreateResourceService struct {
	GeneralParam    *components.GeneralParam
	Params          *CreateResourceParams
	RollBackContext rollback.RollBackObjects
	InstallParams
}

// CreateResourceParams 创建资源 参数 结构体
type CreateResourceParams struct {
	Host          string `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort     int    `json:"query_port" validate:"required"`
	UserName      string `json:"username" validate:"required"`
	Password      string `json:"password" validate:"required"`
	ResourceName  string `json:"resource_name" validate:"required"`
	AccessKey     string `json:"access_key" validate:"required"`
	SecretKey     string `json:"secret_key" validate:"required"`
	Endpoint      string `json:"endpoint" `
	RootPath      string `json:"root_path" validate:"required"`
	BucketName    string `json:"bucket_name" validate:"required"`
	MasterFeIp    string `json:"master_fe_ip" validate:"ip"` // 第一台FE IP
	Region        string `json:"region" validate:"required"`
	RootPassword  string `json:"root_password" `
	AdminPassword string `json:"admin_password" `
}

// CreateResource Metadata操作, 创建资源
func (i *CreateResourceService) CreateResource() (err error) {
	pwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		i.Params.UserName, pwd, i.Params.MasterFeIp, i.Params.QueryPort, ""))

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

	endpoint := ""
	// 若传参为空，会默认拼接COS内网域名，兼容其他S3 对象存储，或公网连接需求
	if i.Params.Endpoint == "" {
		endpoint = fmt.Sprintf(DefaultCosEndpoint, i.Params.Region)
	} else {
		endpoint = i.Params.Endpoint
	}
	akBytes, err := base64.StdEncoding.DecodeString(i.Params.AccessKey)
	if err != nil {
		logger.Error("parse AccessKey failed, %v", err)
		return err
	}
	skBytes, err := base64.StdEncoding.DecodeString(i.Params.SecretKey)
	if err != nil {
		logger.Error("parse SecretKey failed, %v", err)
		return err
	}
	// 拼接 创建资源SQL
	createResSql := fmt.Sprintf(`CREATE RESOURCE "%s"
	PROPERTIES
	(
		"type" = "s3",
		"s3.endpoint" = "%s",
		"s3.region" = "%s",
		"s3.bucket" = "%s",
		"s3.root.path" = "%s",
		"s3.access_key" = "%s",
		"s3.secret_key" = "%s",
		"s3.connection.maximum" = "200",
		"s3.connection.request.timeout" = "60000",
		"s3.connection.timeout" = "60000"
	);`, i.Params.ResourceName, endpoint, i.Params.Region, i.Params.BucketName,
		i.Params.RootPath, string(akBytes), string(skBytes))

	_, err = db.Exec(createResSql)
	if err != nil {
		logger.Error("create doris remote storage resource failed, %v", err)
		return err
	} else {
		return
	}
}

// DropResourceParams 创建资源 参数 结构体
type DropResourceParams struct {
	Host          string `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort     int    `json:"query_port" validate:"required"`
	UserName      string `json:"username" validate:"required"`
	Password      string `json:"password" validate:"required"`
	ResourceName  string `json:"resource_name" validate:"required"`
	MasterFeIp    string `json:"master_fe_ip" validate:"ip"` // 第一台FE IP
	RootPassword  string `json:"root_password" `
	AdminPassword string `json:"admin_password" `
}

// DropResourceService TODO
type DropResourceService struct {
	GeneralParam    *components.GeneralParam
	Params          *DropResourceParams
	RollBackContext rollback.RollBackObjects
	InstallParams
}

// DropResource 更新Metadata
func (i *DropResourceService) DropResource() (err error) {
	pwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		i.Params.UserName, pwd, i.Params.MasterFeIp, i.Params.QueryPort, ""))

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
	// 拼接 删除资源SQL
	dropSql := fmt.Sprintf("drop resource %s;", i.Params.ResourceName)
	_, err = db.Exec(dropSql)
	if err != nil {
		logger.Error("drop doris remote storage resource failed, %v", err)
		return err
	} else {
		return
	}
}
