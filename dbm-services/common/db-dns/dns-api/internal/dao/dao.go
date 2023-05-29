// Package dao TODO
package dao

import (
	"bk-dnsapi/internal/domain/entity"

	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/mysql" // mysql TODO
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

var (
	// DnsDB TODO
	DnsDB *gorm.DB
)

// Init TODO
func Init() error {
	if err := InitDnsDB(); err != nil {
		return err
	}
	return nil
}

// InitDnsDB TODO
func InitDnsDB() error {
	db, err := gorm.Open("mysql", viper.GetString("db.dns_conn"))
	if err != nil {
		return errors.Wrap(err, "init config db failed")
	}
	// 开启SQL,便于排查
	db.LogMode(viper.GetBool("debug"))

	// 自动建表
	// TODO 没建立索引
	if viper.GetBool("db.auto_migration") {
		db.Set("gorm:table_options", "ENGINE=InnoDB").
			Set("gorm:table_options", "CHARSET=utf8").AutoMigrate(
			&entity.TbDnsBase{},
			&entity.TbDnsIdcMap{},
			&entity.TbDnsServer{})
		// 创建索引
		db.Table("tb_dns_base").AddIndex("idx_ip_port", "ip", "port")
		db.Table("tb_dns_base").AddIndex("idx_domain_name_app", "domain_name", "app")
		db.Table("tb_dns_base").AddIndex("idx_app_manager", "app", "manager")
		db.Table("tb_dns_base").AddUniqueIndex("uidx_domain_name_ip_port", "domain_name", "ip", "port")

		db.Table("tb_dns_server").AddUniqueIndex("uidx_ip", "ip")

		db.Table("")
	}
	DnsDB = db
	return nil
}

// Close TODO
func Close() error {
	if err := DnsDB.Close(); err != nil {
		return errors.Wrap(err, "close config db failed")
	}

	return nil
}
