package migratespec

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
	"github.com/sethvargo/go-password/password"
	"gorm.io/gorm"

	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/util/crypt"
)

const SensitiveMigVer = 3

func MigrateSensitive(db *gorm.DB) error {
	confNames := []*model.ConfigNameDefModel{
		// tendb
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "admin_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "repl_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "yw_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "monitor_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "monitor_access_all_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "backup_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "mysql#user", ConfName: "os_mysql_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "proxy#user", ConfName: "proxy_admin_pwd", FlagEncrypt: 1,
		},
		{
			Namespace: "tendb", ConfType: "init_user", ConfFile: "spider#user", ConfName: "tdbctl_pwd", FlagEncrypt: 1,
		},

		{
			Namespace: "tendbha", ConfType: "backup", ConfFile: "binlog_rotate.yaml", ConfName: "encrypt.key_prefix", FlagEncrypt: 1,
		},
		{
			Namespace: "tendbsingle", ConfType: "backup", ConfFile: "binlog_rotate.yaml",
			ConfName: "encrypt.key_prefix", FlagEncrypt: 1,
		},
		{
			Namespace: "tendbcluster", ConfType: "backup", ConfFile: "binlog_rotate.yaml", ConfName: "encrypt.key_prefix", FlagEncrypt: 1,
		},

		// common
		{
			Namespace: "common", ConfType: "osconf", ConfFile: "os", ConfName: "user_pwd", FlagEncrypt: 1,
		},
		// TendisCache
		{
			Namespace: "TendisCache", ConfType: "dbconf", ConfFile: "TendisCache-3.2", ConfName: "requirepass", FlagEncrypt: 1,
		},
		{
			Namespace: "TendisCache", ConfType: "dbconf", ConfFile: "TendisCache-3.2", ConfName: "requirepass1", FlagEncrypt: 1,
		},
		// kafka
		{
			Namespace: "kafka", ConfType: "dbconf", ConfFile: "2.4.0", ConfName: "adminPassword", FlagEncrypt: 1,
		},
		{
			Namespace: "kafka", ConfType: "dbconf", ConfFile: "2.4.0", ConfName: "password", FlagEncrypt: 1,
		},
		// hdfs
		{
			Namespace: "hdfs", ConfType: "dbconf", ConfFile: "2.6.0-cdh5.4.11-tendataV0.2", ConfName: "password", FlagEncrypt: 1,
		},
		// pulsar
		{
			Namespace: "pulsar", ConfType: "dbconf", ConfFile: "2.10.1", ConfName: "password", FlagEncrypt: 1,
		},
		// influxdb
		{
			Namespace: "influxdb", ConfType: "dbconf", ConfFile: "1.8.4", ConfName: "password", FlagEncrypt: 1,
		},
		// es
		{
			Namespace: "es", ConfType: "dbconf", ConfFile: "7.10.2", ConfName: "transport_pemkey_password",
			ValueDefault: "", FlagEncrypt: 1,
		},
		{
			Namespace: "es", ConfType: "dbconf", ConfFile: "7.10.2", ConfName: "http_pemkey_password",
			ValueDefault: "", FlagEncrypt: 1,
		},
	}
	//confNameIdStart := 1000000
	for _, c := range confNames {
		if c.ValueDefault == "" {
			c.ValueDefault = password.MustGenerate(12, 3, 0, false, true)
			logger.Info("sensitive: {Namespace:%s ConfType:%s ConfFile:%s ConfName:%s ValueDefault:%s}",
				c.Namespace, c.ConfType, c.ConfFile, c.ConfName, c.ValueDefault)
			if c.FlagEncrypt == 1 {
				key := fmt.Sprintf("%s%s", config.GetString("encrypt.keyPrefix"), constvar.BKBizIDForPlat)
				c.ValueDefault, _ = crypt.EncryptString(c.ValueDefault, key, constvar.EncryptEnableZip)
			}
		}
		//c.ID = uint64(confNameIdStart + i)
		c.ValueType = "STRING"
		c.ValueTypeSub = ""
		c.ValueAllowed = ""
		c.FlagStatus = 1
	}
	err := db.Transaction(func(tx *gorm.DB) error {

		if err1 := tx.Omit("id", "value_formula", "order_index", "since_version", "stage").
			Create(confNames).Error; err1 != nil {
			return errors.WithMessage(err1, "init sensitive conf_name")
		}
		/*
			if err1 := tx.Select("value_default", "flag_encrypt").
				Where(c.UniqueWhere()).Updates(c).Error; err1 != nil {
				return errors.WithMessage(err1, c.ConfName)
			}
		*/
		return nil
	})
	return err
}
