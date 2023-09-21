package assests

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/service"
	"embed"
	"encoding/json"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/mysql" // mysql TODO
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/pkg/errors"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
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
		mig, err = migrate.NewWithSourceInstance("iofs", d, dbURL)
		if err != nil {
			return errors.WithMessage(err, "migrate from embed")
		}
		defer mig.Close()
		err = mig.Up()
		if err == nil {
			slog.Info("migrate source from embed success")
			return nil
		} else if err == migrate.ErrNoChange {
			slog.Info("migrate source from embed success with", "msg", err.Error())
			return nil
		} else {
			slog.Error("migrate source from embed failed", err)
			return err
		}
	}
}
func DoMigratePlatformPassword() error {
	// 初始化安全规则
	passwordSecurityRule := &service.SecurityRulePara{Name: "password",
		Rule: "{\"max_length\":12,\"min_length\":8,\"include_rule\":{\"numbers\":true,\"symbols\":true,\"lowercase\":true,\"uppercase\":true},\"exclude_continuous_rule\":{\"limit\":4,\"letters\":false,\"numbers\":false,\"symbols\":false,\"keyboards\":false,\"repeats\":false}}", Operator: "admin"}
	b, _ := json.Marshal(passwordSecurityRule)
	errOuter := passwordSecurityRule.AddSecurityRule(string(b))
	if errOuter != nil {
		no, _ := errno.DecodeErr(errOuter)
		if no != errno.RuleExisted.Code {
			return errOuter
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
			defaultCloudId := int64(0)
			getPara := &service.GetPasswordPara{Users: []service.UserInComponent{{user, component.Component}},
				Instances: []service.Address{{"0.0.0.0", 0, &defaultCloudId}}}
			exists, err := getPara.GetPassword()
			if err != nil {
				return fmt.Errorf("%s error: %s", "init platform password, get password", err.Error())
			}
			if len(exists) == 0 {
				insertPara := &service.ModifyPasswordPara{UserName: user, Component: component.Component, Operator: "admin",
					Instances: []service.Address{{"0.0.0.0", 0, &defaultCloudId}}, SecurityRuleName: "password"}
				err = insertPara.ModifyPassword()
				if err != nil {
					return fmt.Errorf("%s error: %s", "init platform password, modify password", err.Error())
				}
			}
		}
	}
	return nil
}
