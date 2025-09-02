package import_grants_file

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/listener"

	"slices"
	"strings"
)

func (c *ImportGrantsFile) ModifyPrivs() (err error) {
	listeners, err := c.loadPrivFileToListeners(c.Params.Filename)
	if err != nil {
		return err
	}
	logger.Info("loaded privileges file to listeners finished")

	// 修改授权 ip
	for _, l := range listeners {
		for _, ao := range l.AuthOptions {
			ao.Username = strings.Replace(ao.Username, c.Params.SourceIp, c.destIp, -1)
		}
	}
	logger.Info("replace source ip to dest ip finished")

	if c.needMigrate() {
		// 先扫描一遍, 找出一个用户的 grant 语句都没密码的
		// 也就是在 5.6 下, 这个账号就没有密码
		userAuthOptionMap := make(map[string]bool)
		for _, l := range listeners {
			for _, ao := range l.AuthOptions {
				if _, ok := userAuthOptionMap[ao.Username]; !ok {
					userAuthOptionMap[ao.Username] = false
				}
				userAuthOptionMap[ao.Username] = userAuthOptionMap[ao.Username] || ao.AuthClause != ""
			}
		}
		logger.Info("scan no password user finished")

		// 给密码的账号伪造 create
		for k, v := range userAuthOptionMap {
			if v {
				continue
			}

			l := &listener.PrivListener{
				StatementType: listener.PrivStatementCreate,
				AuthOptions: []*listener.AuthOptionStruct{
					{
						Username: k,
					},
				},
			}
			// 必须插入到最前面去
			listeners = append([]*listener.PrivListener{l}, listeners...)
		}
		logger.Info("generate create statement for no password user finished")

		for _, l := range listeners {
			if l.StatementType == listener.PrivStatementGrant && l.GrantType == listener.GrantStatementTypeNormal {
				idx := slices.IndexFunc(l.AuthOptions, func(ao *listener.AuthOptionStruct) bool {
					return ao.AuthClause != ""
				})
				if idx >= 0 {
					createListener := l.Copy()
					createListener.StatementType = listener.PrivStatementCreate
					for _, ao := range createListener.AuthOptions {
						// show grants IDENTIFIED BY [PASSWORD] 'password' 5.6 上没其他的
						ao.AuthClause = strings.Replace(ao.AuthClause, "IDENTIFIED BY PASSWORD", "IDENTIFIED WITH 'mysql_native_password' AS", -1)
					}
					c.finalListeners = append(c.finalListeners, createListener)

					grantListener := l.Copy()
					grantListener.StatementType = listener.PrivStatementGrant
					grantListener.GrantType = listener.GrantStatementTypeNormal
					for _, ao := range grantListener.AuthOptions {
						ao.AuthClause = ""
					}
					c.finalListeners = append(c.finalListeners, grantListener)

					continue
				}
			}
			c.finalListeners = append(c.finalListeners, l)
		}
	} else {
		c.finalListeners = listeners
	}
	logger.Info("migrate statement finished")
	return nil
}

func (c *ImportGrantsFile) generateCreate(listeners []*listener.PrivListener) error {
	// 先扫描一遍, 找出一个用户的 grant 语句都没密码的
	// 也就是在 5.6 下, 这个账号就没有密码
	userAuthOptionMap := make(map[string]bool)
	for _, l := range listeners {
		for _, ao := range l.AuthOptions {
			if _, ok := userAuthOptionMap[ao.Username]; !ok {
				userAuthOptionMap[ao.Username] = false
			}
			userAuthOptionMap[ao.Username] = userAuthOptionMap[ao.Username] || ao.AuthClause != ""
		}
	}
	logger.Info("scan no password user finished")

	return nil
}
