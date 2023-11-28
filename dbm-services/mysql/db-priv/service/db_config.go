package service

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"

	"dbm-services/mysql/priv-service/util"
)

// DbconfigUrl dbconfig的url
const DbconfigUrl = "/bkconfig/v1/confitem/query"

// NamePassword 用户名、密码
type NamePassword struct {
	Name     string
	Password string
}

// ComponentPlatformUser 组件、用户名、密码
type ComponentPlatformUser struct {
	Component    string
	NamePassword []NamePassword
}

// Config dbconfig中的配置信息
type Config struct {
	BkBizId      string `json:"bk_biz_id"`
	LevelName    string `json:"level_name"`
	LevelValue   string `json:"level_value"`
	ConfFileInfo struct {
		Namespace     string `json:"namespace"`
		ConfType      string `json:"conf_type"`
		ConfFile      string `json:"conf_file"`
		ConfTypeLc    string `json:"conf_type_lc"`
		ConfFileLc    string `json:"conf_file_lc"`
		NamespaceInfo string `json:"namespace_info"`
		Description   string `json:"description"`
		UpdatedBy     string `json:"updated_by"`
		CreatedAt     string `json:"created_at"`
		UpdatedAt     string `json:"updated_at"`
	} `json:"conf_file_info"`
	Content struct {
		// redis os
		User    string `json:"user"`
		UserPwd string `json:"user_pwd"`
		// mysql admin
		AdminPwd             string `json:"admin_pwd"`
		AdminUser            string `json:"admin_user"`
		BackupPwd            string `json:"backup_pwd"`
		BackupUser           string `json:"backup_user"`
		MonitorAccessAllPwd  string `json:"monitor_access_all_pwd"`
		MonitorAccessAllUser string `json:"monitor_access_all_user"`
		// mysql monitor
		MonitorPwd  string `json:"monitor_pwd"`
		MonitorUser string `json:"monitor_user"`
		// mysql os
		OsMysqlPwd  string `json:"os_mysql_pwd"`
		OsMysqlUser string `json:"os_mysql_user"`
		// mysql repl
		ReplPwd  string `json:"repl_pwd"`
		ReplUser string `json:"repl_user"`
		// mysql yw
		YwPwd  string `json:"yw_pwd"`
		YwUser string `json:"yw_user"`
		// proxy user
		ProxyAdminPwd  string `json:"proxy_admin_pwd"`
		ProxyAdminUser string `json:"proxy_admin_user"`
	} `json:"content"`
}

// GetConfigPara dbconfig入参
type GetConfigPara struct {
	BkBizId    string `json:"bk_biz_id"`
	LevelName  string `json:"level_name"`
	LevelValue string `json:"level_value"`
	ConfFile   string `json:"conf_file"`
	ConfType   string `json:"conf_type"`
	Namespace  string `json:"namespace"`
	Format     string `json:"format"`
}

// GetRedisOsUser 获取redis os帐号密码
func GetRedisOsUser(users *[]ComponentPlatformUser, host string) error {
	para := GetConfigPara{BkBizId: "0", LevelName: "plat", LevelValue: "0",
		ConfFile: "os", ConfType: "osconf", Namespace: "common", Format: "map"}
	// 获取配置
	config, err := para.GetConfig(host)
	if err != nil {
		return err
	}
	user := ComponentPlatformUser{Component: "redis", NamePassword: []NamePassword{
		{config.Content.User, config.Content.UserPwd}}}
	*users = append(*users, user)
	return nil
}

// GetMysqlInitUser 获取mysql帐号密码
func GetMysqlInitUser(users *[]ComponentPlatformUser, host string) error {
	para := GetConfigPara{BkBizId: "0", LevelName: "plat", LevelValue: "0",
		ConfFile: "mysql#user", ConfType: "init_user", Namespace: "tendb", Format: "map"}
	// 获取配置
	config, err := para.GetConfig(host)
	if err != nil {
		return err
	}
	content := config.Content
	// 获取密码不为空
	if content.BackupPwd == "" || content.MonitorPwd == "" || content.MonitorAccessAllPwd ==
		"" || content.ReplPwd == "" || content.YwPwd == "" || content.OsMysqlPwd == "" {
		return fmt.Errorf("some passwords null:%v", content)
	}
	// 添加平台密码
	user := ComponentPlatformUser{Component: "mysql", NamePassword: []NamePassword{
		{"dba_bak_all_sel", content.BackupPwd},
		{"MONITOR", content.MonitorPwd},
		{"MONITOR_ALL", content.MonitorAccessAllPwd},
		{"mysql", content.OsMysqlPwd},
		{"repl", content.ReplPwd},
		{"yw", content.YwPwd}}}
	*users = append(*users, user)
	return nil
}

// GetProxyInitUser 获取proxy账户密码
func GetProxyInitUser(users *[]ComponentPlatformUser, host string) error {
	para := GetConfigPara{BkBizId: "0", LevelName: "plat", LevelValue: "0",
		ConfFile: "proxy#user", ConfType: "init_user", Namespace: "tendb", Format: "map"}
	config, err := para.GetConfig(host)
	if err != nil {
		return err
	}
	if config.Content.ProxyAdminPwd == "" {
		return fmt.Errorf("password null:%v", config.Content)
	}
	user := ComponentPlatformUser{Component: "proxy",
		NamePassword: []NamePassword{{"proxy", config.Content.ProxyAdminPwd}}}
	*users = append(*users, user)
	return nil
}

// GetConfig 访问dbconfig接口获取信息
func (m *GetConfigPara) GetConfig(host string) (Config, error) {
	var configs []Config
	var config Config
	c := util.NewClientByHosts(host)
	result, err := c.Do(http.MethodPost, DbconfigUrl, m)
	if err != nil {
		slog.Error("msg", DbconfigUrl, err)
		return config, err
	}
	if err = json.Unmarshal(result.Data, &configs); err != nil {
		slog.Error("msg", "host", host, "url", DbconfigUrl, "error", err)
		return config, err
	}
	// 一次仅查询一个类别的配置
	if len(configs) != 1 {
		return config, fmt.Errorf("want get 1 config, but get %d", len(configs))
	}
	return configs[0], nil
}
