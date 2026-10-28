package dao

import (
	"net"
	"time"

	"bk-dnsapi/internal/domain/entity"
	"dbm-services/common/go-pubpkg/kms"

	"github.com/go-sql-driver/mysql"
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

var (
	DnsDB *gorm.DB
)

// Init 初始化
func Init() error {
	if err := InitDnsDB(); err != nil {
		return err
	}
	return nil
}

// InitDnsDB 初始化DB
func InitDnsDB() error {
	username := viper.GetString("db.username")
	password := viper.GetString("db.password")
	credentials, err := loadRuntimeCredentials()
	if err != nil {
		return errors.Wrap(err, "load DNS API KMS credentials failed")
	}
	if credentials != nil {
		username = credentials.MySQL.DbDnsApi.Username
		password = credentials.MySQL.DbDnsApi.Password
	}

	config := mysql.NewConfig()
	config.User = username
	config.Passwd = password
	config.Net = "tcp"
	config.Addr = net.JoinHostPort(viper.GetString("db.addr"), viper.GetString("db.port"))
	config.DBName = viper.GetString("db.name")
	config.Params = map[string]string{"charset": "utf8"}
	config.ParseTime = true
	config.Loc = time.Local

	db, err := gorm.Open("mysql", config.FormatDSN())
	if err != nil {
		return errors.Wrap(err, "init config db failed")
	}
	// 开启SQL,便于排查
	db.LogMode(viper.GetBool("debug"))

	// 自动建表
	if viper.GetBool("db.auto_migration") {
		db.Set("gorm:table_options", "ENGINE=InnoDB").
			Set("gorm:table_options", "CHARSET=utf8").AutoMigrate(
			&entity.TbDnsBase{},
			&entity.TbDnsIdcMap{},
			&entity.TbDnsServer{},
			&entity.TbDnsConfig{})
		// 创建索引
		db.Table("tb_dns_base").AddIndex("idx_ip_port", "ip", "port")
		db.Table("tb_dns_base").AddIndex("idx_domain_name_app", "domain_name", "app")
		db.Table("tb_dns_base").AddIndex("idx_app_manager", "app", "manager")
		db.Table("tb_dns_base").AddUniqueIndex("uidx_domain_name_ip_port", "domain_name", "ip", "port")

		db.Table("tb_dns_server").AddUniqueIndex("uidx_ip", "ip")
		db.Table("tb_dns_config").AddUniqueIndex("inx_p", "paraname")
	}
	DnsDB = db
	return nil
}

type RuntimeCredentials struct {
	MySQL struct {
		DbDnsApi struct {
			Username string `json:"username"`
			Password string `json:"password"`
		} `json:"dbDnsApi"`
	} `json:"mysql"`
}

func loadRuntimeCredentials() (*RuntimeCredentials, error) {
	enabled, err := kms.Enabled()
	if err != nil || !enabled {
		return nil, err
	}

	plaintext, enabled, err := kms.LoadEnvelope(kms.LoadOptions{
		CredentialDirEnv: "DB_DNS_API_KMS_CREDENTIAL_DIR",
	})
	if err != nil {
		return nil, err
	}
	if !enabled {
		return nil, errors.New("KMS disabled while loading DNS API credentials")
	}

	var credentials RuntimeCredentials
	if err := kms.DecodeJSON(plaintext, &credentials); err != nil {
		return nil, err
	}
	for _, field := range []struct{ name, value string }{
		{"mysql.dbDnsApi.username", credentials.MySQL.DbDnsApi.Username},
		{"mysql.dbDnsApi.password", credentials.MySQL.DbDnsApi.Password},
	} {
		if err := kms.RequireNonEmpty(field.value, field.name); err != nil {
			return nil, err
		}
	}
	return &credentials, nil
}

// Close 关闭连接
func Close() error {
	if err := DnsDB.Close(); err != nil {
		return errors.Wrap(err, "close config db failed")
	}

	return nil
}
