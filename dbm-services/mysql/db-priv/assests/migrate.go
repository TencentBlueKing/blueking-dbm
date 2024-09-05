package assests

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"embed"
	"encoding/json"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
	"time"

	"github.com/golang-migrate/migrate/v4/database"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/mysql" // mysql TODO
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

//go:embed migrations/*.sql
var fs embed.FS

// DoMigrateFromEmbed 先尝试从 go embed 文件系统查找 migrations
// no changes: return nil
func DoMigrateFromEmbed() error {
	var mig *migrate.Migrate
	if d, err := iofs.New(fs, "migrations"); err != nil {
		return err
	} else {
		dbURL := fmt.Sprintf(
			"mysql://%s:%s@tcp(%s)/%s?charset=%s&parseTime=true&loc=Local&multiStatements=true&interpolateParams=true",
			viper.GetString("db.username"),
			viper.GetString("db.password"),
			viper.GetString("db.addr"),
			viper.GetString("db.name"),
			"utf8",
		)
		i := 1
		for ; i <= 10; i++ {
			mig, err = migrate.NewWithSourceInstance("iofs", d, dbURL)
			if err == nil {
				break
			} else if err == database.ErrLocked {
				slog.Error(fmt.Sprintf("try %d time", i), "migrate from embed error", err)
				if i == 10 {
					slog.Error("try too many times")
					return errors.WithMessage(err, "migrate from embed")
				}
				time.Sleep(3 * time.Minute)
			} else {
				return errors.WithMessage(err, "migrate from embed")
			}
		}

		defer mig.Close()
		err = mig.Up()
		if err == nil {
			slog.Info("migrate source from embed success")
		} else if err == migrate.ErrNoChange {
			slog.Info("migrate source from embed success with", "msg", err.Error())
		} else {
			slog.Error("migrate source from embed failed", err)
			return err
		}
		// 版本4添加了字段，需要在migrate后填充字段值
		version, dirty, errInner := mig.Version()
		if errInner == nil && version == 10 && dirty == false {
			err = ModifyPrivsGlobalToGlobalNon()
			if err != nil {
				return fmt.Errorf("modify some priv from global to non-global error after migration version 10")
			}
		}
		return nil
	}
}

func DoMigratePlatformPassword() error {
	// 兼容历史版本，避免未同步调整，引起旧规则无法使用
	oldRules := []string{"password", "mongo_password", "redis_password", "simple_password"}
	for _, old := range oldRules {
		SecurityRulePara := &service.SecurityRulePara{Name: old}
		rule, err := SecurityRulePara.GetSecurityRule()
		if err != nil {
			continue
		}
		var v2 string
		switch old {
		case "password":
			v2 = service.MysqlSqlserverRule
		case "mongo_password":
			v2 = service.MongodbRule
		case "redis_password":
			v2 = service.RedisRule
		case "simple_password":
			v2 = service.BigDataRule
		default:
			continue
		}
		SecurityRulePara = &service.SecurityRulePara{Id: rule.Id, Rule: v2, Operator: "deprecated"}
		b, _ := json.Marshal(SecurityRulePara)
		err = SecurityRulePara.ModifySecurityRule(string(b), "modify_security_rule")
		if err != nil {
			slog.Error("modify_security_rule", "name", old, "error", err)
		}
	}

	// 初始化新版本安全规则
	// 密码服务V2版本，各个组件有独立的安全规则
	bigData := []string{"es_password", "kafka_password", "hdfs_password", "pulsar_password",
		"influxdb_password", "doris_password"}
	mysqlSqlserver := []string{"mysql_password", "tendbcluster_password", "sqlserver_password"}
	for _, name := range bigData {
		err := AddRule(name, service.BigDataRule)
		if err != nil {
			return err
		}
	}
	for _, name := range mysqlSqlserver {
		err := AddRule(name, service.MysqlSqlserverRule)
		if err != nil {
			return err
		}
	}
	err := AddRule("redis_password_v2", service.RedisRule)
	if err != nil {
		return err
	}
	err = AddRule("mongodb_password", service.MongodbRule)
	if err != nil {
		return err
	}

	// 初始化平台密码，随机密码
	type ComponentPlatformUser struct {
		Component string
		Usernames []string
	}

	// 平台密码初始化，不存在则新增
	var users []ComponentPlatformUser
	users = append(users, ComponentPlatformUser{Component: "mysql", Usernames: []string{
		"dba_bak_all_sel", "MONITOR", "MONITOR_ALL", "mysql", "repl", "yw", "partition_yw"}})
	users = append(users, ComponentPlatformUser{Component: "proxy", Usernames: []string{"proxy"}})
	users = append(users, ComponentPlatformUser{Component: "tbinlogdumper", Usernames: []string{"ADMIN"}})
	users = append(users, ComponentPlatformUser{Component: "redis", Usernames: []string{"mysql"}})

	for _, component := range users {
		for _, user := range component.Usernames {
			defaultInt := int64(0)
			getPara := &service.GetPasswordPara{Users: []service.UserInComponent{{user,
				component.Component}},
				Instances: []service.Address{{"0.0.0.0", &defaultInt, &defaultInt}}}
			_, count, err := getPara.GetPassword()
			if err != nil {
				return fmt.Errorf("%s error: %s", "init platform password, get password", err.Error())
			}
			if count == 0 {
				insertPara := &service.ModifyPasswordPara{UserName: user, Component: component.Component, Operator: "admin",
					Instances:    []service.Address{{"0.0.0.0", &defaultInt, &defaultInt}},
					InitPlatform: true, SecurityRuleName: "password"}
				if component.Component == "redis" {
					insertPara = &service.ModifyPasswordPara{UserName: user, Component: component.Component, Operator: "admin",
						Instances:    []service.Address{{"0.0.0.0", &defaultInt, &defaultInt}},
						InitPlatform: true, SecurityRuleName: "redis_password"}
				}
				b, _ := json.Marshal(*insertPara)
				err = insertPara.ModifyPassword(string(b), "modify_password")
				if err != nil {
					return fmt.Errorf("%s error: %s", "init platform password, modify password", err.Error())
				}
			}
		}
	}
	return nil
}

func AddRule(name string, content string) error {
	rule := &service.SecurityRulePara{Name: name,
		Rule: content, Operator: "admin"}
	b, _ := json.Marshal(rule)
	err := rule.AddSecurityRule(string(b), "add_security_rule")
	if err != nil {
		no, _ := errno.DecodeErr(err)
		if no != errno.RuleExisted.Code {
			slog.Error("add_rule", "name", name, "error", err)
			return err
		}
	}
	return nil
}

func ModifyPrivsGlobalToGlobalNon() error {
	var rules []*service.TbAccountRules
	err := service.DB.Self.Model(&service.TbAccountRules{}).Scan(&rules).Error
	if err != nil {
		slog.Error("msg", "ModifySomePrivsFromGlobalToNonGlobal select rules error", err)
		return err
	}
	pattern := regexp.MustCompile(`,+`)
	// 对于已存在的权限规，trigger、event、create routine、alter routine 调整授权范围从global到database
	privs := []string{"trigger", "event", "create routine", "alter routine"}
	for _, rule := range rules {
		var updateFlag bool
		for _, priv := range privs {
			if strings.Contains(rule.GlobalPriv, priv) {
				updateFlag = true
				rule.GlobalPriv = strings.Replace(rule.GlobalPriv, priv, "", -1)
				rule.DmlDdlPriv = fmt.Sprintf("%s,%s", rule.DmlDdlPriv, priv)
			}
		}
		if updateFlag {
			rule.GlobalPriv = pattern.ReplaceAllString(rule.GlobalPriv, ",")
			rule.GlobalPriv = strings.Trim(rule.GlobalPriv, ",")
			priv := map[string]string{"dml": rule.DmlDdlPriv, "global": rule.GlobalPriv}
			para := service.AccountRulePara{BkBizId: rule.BkBizId, ClusterType: &rule.ClusterType, Id: rule.Id,
				AccountId: rule.AccountId, Dbname: rule.Dbname, Priv: priv, Operator: rule.Operator}
			log, _ := json.Marshal(para)
			errInner := (&para).ModifyAccountRule(string(log), "modify_account_rule")
			if errInner != nil {
				return errInner
			}
		}
	}
	return nil
}
