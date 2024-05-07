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
	// 初始化安全规则
	// 通用的安全规则
	passwordSecurityRule := &service.SecurityRulePara{Name: "password",
		Rule: "{\"max_length\":12,\"min_length\":8,\"include_rule\":{\"numbers\":true,\"symbols\":true,\"lowercase\":true,\"uppercase\":true},\"exclude_continuous_rule\":{\"limit\":4,\"letters\":false,\"numbers\":false,\"symbols\":false,\"keyboards\":false,\"repeats\":false}}", Operator: "admin"}
	b, _ := json.Marshal(passwordSecurityRule)
	errOuter := passwordSecurityRule.AddSecurityRule(string(b), "add_security_rule")
	if errOuter != nil {
		no, _ := errno.DecodeErr(errOuter)
		if no != errno.RuleExisted.Code {
			return errOuter
		}
	}

	// 不需要符号、固定长度的安全规则
	NoSymbols := []string{"mongo_password", "redis_password", "simple_password"}
	// mongodb专用的安全规则
	for _, name := range NoSymbols {
		passwordSecurityRule = &service.SecurityRulePara{Name: name,
			Rule: "{\"max_length\":16,\"min_length\":16,\"include_rule\":{\"numbers\":true,\"symbols\":false,\"lowercase\":true,\"uppercase\":true},\"exclude_continuous_rule\":{\"limit\":4,\"letters\":false,\"numbers\":false,\"symbols\":false,\"keyboards\":false,\"repeats\":false}}", Operator: "admin"}
		b, _ = json.Marshal(passwordSecurityRule)
		errOuter = passwordSecurityRule.AddSecurityRule(string(b), "add_security_rule")
		if errOuter != nil {
			no, _ := errno.DecodeErr(errOuter)
			if no != errno.RuleExisted.Code {
				return errOuter
			}
		}
	}

	// 初始化平台密码，随机密码
	type ComponentPlatformUser struct {
		Component string
		Usernames []string
	}

	// 平台密码初始化，不存在新增
	var users []ComponentPlatformUser
	users = append(users, ComponentPlatformUser{Component: "mysql", Usernames: []string{
		"dba_bak_all_sel", "MONITOR", "MONITOR_ALL", "mysql", "repl", "yw"}})
	users = append(users, ComponentPlatformUser{Component: "proxy", Usernames: []string{"proxy"}})
	users = append(users, ComponentPlatformUser{Component: "tbinlogdumper", Usernames: []string{"ADMIN"}})

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
				b, _ = json.Marshal(*insertPara)
				err = insertPara.ModifyPassword(string(b), "modify_password")
				if err != nil {
					return fmt.Errorf("%s error: %s", "init platform password, modify password", err.Error())
				}
			}
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
