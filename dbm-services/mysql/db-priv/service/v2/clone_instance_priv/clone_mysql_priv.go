package clone_instance_priv

import (
	"dbm-services/mysql/priv-service/service/v2/clone_instance_priv/internal/mysql"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"fmt"
)

func (c *CloneInstancePrivPara) cloneMySQLPriv(isStorage bool) error {
	v, isSpider, err := internal.QueryMySQLVersion(*c.BkCloudId, c.Source.Address)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("query source mysql version, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}
	c.sourceMySQLVersion = v
	c.logger.Info(
		fmt.Sprintf("source mysql version: %d", v),
	)

	if isSpider {
		if v == 80 { // spider-4
			c.SystemUsers = append(c.SystemUsers, []string{"mariadb.sys", "PUBLIC"}...) // 这个是目前发现 spider 4 特有的
		}
	}

	userList, err := mysql.QueryUserList(*c.BkCloudId, c.Source.Address, c.SystemUsers, c.Target.Address, c.logger)
	if err != nil {
		return err
	}

	c.logger.Info(
		fmt.Sprintf("query mysql user list, users count: %d", len(userList)),
	)

	v, _, err = internal.QueryMySQLVersion(*c.BkCloudId, c.Target.Address)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("query target mysql version, address: %s, err: %s", c.Target.Address, err.Error()),
		)
		return err
	}
	c.targetMySQLVersion = v
	c.logger.Info(
		fmt.Sprintf("target mysql version: %d", v),
	)

	privs, err := mysql.QueryUserPriv(
		*c.BkCloudId, c.Source.Address, userList, c.sourceMySQLVersion >= 57 && isStorage, c.logger)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("query users priv, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}
	c.logger.Info(
		fmt.Sprintf("query users priv, users count: %d", len(privs)),
	)

	// 这个函数其实不会失败
	// 只会生成一些奇怪的 sql
	// 最后会在 import 的时候失败
	privs, err = mysql.ProcessGrantSql(
		privs, c.Source.Address, c.Target.Address, c.sourceMySQLVersion, c.targetMySQLVersion, isStorage, c.logger,
	)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("process grant sql, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}
	c.logger.Info(fmt.Sprintf("grant sql process success, priv count: %d", len(privs)))

	err = mysql.ImportPriv(*c.BkCloudId, c.Target.Address, privs, c.logger)
	if err != nil {
		c.logger.Error(
			fmt.Sprintf("import priv, address: %s, err: %s", c.Source.Address, err.Error()),
		)
		return err
	}

	c.logger.Info("clone mysql priv finish")
	return nil
}
