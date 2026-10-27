// Package config 配置
package config

import (
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/spf13/viper"
)

// DefaultMySQLDTSMasterPort DTS Master 默认 OpenAPI 端口, 与 dbm-ui MYSQL_DTS_MASTER_PORT 保持一致
const DefaultMySQLDTSMasterPort = 18301

// RuntimeConfig 运行配置
var RuntimeConfig *runtimeConfig

// LogConfig 日志配置
var LogConfig *logConfig

type runtimeConfig struct {
	Concurrent                int
	MySQLAdminUser            string
	MySQLAdminPassword        string
	ProxyAdminUser            string
	ProxyAdminPassword        string
	WebConsoleUser            string
	WebConsolePassword        string
	Timezone                  string
	SqlserverAdminUser        string
	SqlserverAdminPassword    string
	SqlserverDataReadUser     string
	SqlserverDataReadPassword string
	SqlserverSySReadUser      string
	SqlserverSySReadPassword  string
	Port                      int
	ParserBin                 string
	CAFile                    string
	CertFile                  string
	KeyFile                   string
	TLS                       bool
	// MySQLDTSMasterPorts v2/mysql-dts/rpc 允许转发的 DTS Master 端口集合
	MySQLDTSMasterPorts map[int]struct{}
}

// parsePorts 解析逗号分隔的端口列表, 非法项忽略并告警, 结果为空时回落到默认端口
func parsePorts(raw string) map[int]struct{} {
	ports := make(map[int]struct{})
	for _, s := range strings.Split(raw, ",") {
		s = strings.TrimSpace(s)
		if s == "" {
			continue
		}
		p, err := strconv.Atoi(s)
		if err != nil || p <= 0 || p > 65535 {
			slog.Warn("ignore invalid mysql_dts_master_ports item", slog.String("item", s))
			continue
		}
		ports[p] = struct{}{}
	}
	if len(ports) == 0 {
		slog.Warn("mysql_dts_master_ports empty or invalid, fallback to default",
			slog.String("raw", raw),
			slog.Int("default", DefaultMySQLDTSMasterPort),
		)
		ports[DefaultMySQLDTSMasterPort] = struct{}{}
	}
	return ports
}

type logConfig struct {
	Console    bool   `yaml:"console"`
	LogFileDir string `yaml:"log_file_dir"`
	Debug      bool   `yaml:"debug"`
	Source     bool   `yaml:"source"`
	Json       bool   `yaml:"json"`
}

// InitConfig 初始化配置
func InitConfig() {
	RuntimeConfig = &runtimeConfig{
		Concurrent:                viper.GetInt("concurrent"),
		MySQLAdminUser:            viper.GetString("mysql_admin_user"),
		MySQLAdminPassword:        viper.GetString("mysql_admin_password"),
		ProxyAdminUser:            viper.GetString("proxy_admin_user"),
		ProxyAdminPassword:        viper.GetString("proxy_admin_password"),
		WebConsoleUser:            viper.GetString("webconsole_user"),
		WebConsolePassword:        viper.GetString("webconsole_password"),
		Timezone:                  viper.GetString("time_zone"),
		SqlserverAdminUser:        viper.GetString("sqlserver_admin_user"),
		SqlserverAdminPassword:    viper.GetString("sqlserver_admin_password"),
		SqlserverDataReadUser:     viper.GetString("sqlserver_data_read_user"),
		SqlserverDataReadPassword: viper.GetString("sqlserver_data_read_password"),
		SqlserverSySReadUser:      viper.GetString("sqlserver_sys_read_user"),
		SqlserverSySReadPassword:  viper.GetString("sqlserver_sys_read_password"),
		Port:                      viper.GetInt("port"),
		ParserBin:                 viper.GetString("tmysqlparser_bin"),
		TLS:                       viper.GetBool("tls"),
		CAFile:                    viper.GetString("ca_file"),
		CertFile:                  viper.GetString("cert_file"),
		KeyFile:                   viper.GetString("key_file"),
		MySQLDTSMasterPorts:       parsePorts(viper.GetString("mysql_dts_master_ports")),
	}

	if !filepath.IsAbs(RuntimeConfig.ParserBin) {
		executable, _ := os.Executable()
		RuntimeConfig.ParserBin = filepath.Join(filepath.Dir(executable), RuntimeConfig.ParserBin)
	}

	LogConfig = &logConfig{
		Console:    viper.GetBool("log_console"),
		LogFileDir: viper.GetString("log_file_dir"),
		Debug:      viper.GetBool("log_debug"),
		Source:     viper.GetBool("log_source"),
		Json:       viper.GetBool("log_json"),
	}

	InitGlobalSemaphore()
}
