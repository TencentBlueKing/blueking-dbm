package dao

import (
	"bk-dnsapi/internal/domain/entity"

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
	db, err := gorm.Open("mysql", viper.GetString("db.dns_conn"))
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

// Close 关闭连接
func Close() error {
	if err := DnsDB.Close(); err != nil {
		return errors.Wrap(err, "close config db failed")
	}

	return nil
}
