package cmd

import (
	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	"dbm-services/common/reverseapi/pkg/core"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
	"os/user"
	"strconv"

	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/maps"
	"gopkg.in/yaml.v2"
)

var subCmdGenConfig = &cobra.Command{
	Use:   "gen-config",
	Short: "Generate config file",
	Long:  `Generate config file`,
	RunE: func(cmd *cobra.Command, args []string) error {
		err := generateRuntimeConfigs()
		if err != nil {
			return err
		}

		err = generateItemsConfigs()
		if err != nil {
			return err
		}

		return nil
	},
}

func init() {
	subCmdGenConfig.PersistentFlags().StringSliceP("nginx-address", "", nil, "nginx-address")
	subCmdGenConfig.PersistentFlags().IntP("bk-cloud-id", "", 0, "bk-cloud-id")
	subCmdGenConfig.PersistentFlags().IntSliceP("port", "", nil, "port")
	_ = subCmdGenConfig.MarkFlagRequired("nginx-address")
	_ = subCmdGenConfig.MarkFlagRequired("bk-cloud-id")
	_ = subCmdGenConfig.MarkFlagRequired("port")

	// 调试代码
	subCmdGenConfig.PersistentFlags().StringP("debug-ip", "", "", "debug ip")
	subCmdGenConfig.PersistentFlags().StringP("debug-monitor-root", "", "", "debug monitor-root")

	_ = viper.BindPFlag("nginx-address", subCmdGenConfig.PersistentFlags().Lookup("nginx-address"))
	_ = viper.BindPFlag("bk-cloud-id", subCmdGenConfig.PersistentFlags().Lookup("bk-cloud-id"))
	_ = viper.BindPFlag("port", subCmdGenConfig.PersistentFlags().Lookup("port"))

	_ = viper.BindPFlag("debug-ip", subCmdGenConfig.PersistentFlags().Lookup("debug-ip"))
	_ = viper.BindPFlag("debug-monitor-root", subCmdGenConfig.PersistentFlags().Lookup("debug-monitor-root"))

	rootCmd.AddCommand(subCmdGenConfig)
}

func generateRuntimeConfigs() error {
	nginxAddrs := viper.GetStringSlice("nginx-address")
	bkCloudId := viper.GetInt("bk-cloud-id")
	ports := viper.GetIntSlice("port")

	apiCore, err := core.NewCoreWithAddr(int64(bkCloudId), nginxAddrs, core.DefaultRetryOpts...)
	if err != nil {
		return err
	}

	data, err := reversemysqlapi.MonitorRuntimeConfig(apiCore, ports...)
	if err != nil {
		return err
	}

	var runtimeConfigs []config.Config
	err = yaml.Unmarshal(data, &runtimeConfigs)
	if err != nil {
		return err
	}

	monitorInstallPath := cst.MySQLMonitorInstallPath
	if viper.GetString("debug-monitor-root") != "" {
		slog.Info("generate runtime configs", slog.String("debug monitor root", viper.GetString("debug-monitor-root")))
		monitorInstallPath = viper.GetString("debug-monitor-root")
	}

	logDir := filepath.Join(monitorInstallPath, "logs")
	for _, ele := range runtimeConfigs {
		err := generateOneRuntimeConfig(&ele, &logDir)
		if err != nil {
			return err
		}
	}

	return nil
}

func generateOneRuntimeConfig(cfg *config.Config, logDir *string) error {
	cfg.Log = &config.LogConfig{
		Console:    false,
		LogFileDir: logDir,
		Debug:      false,
		Source:     true,
		Json:       true,
	}

	monitorInstallPath := cst.MySQLMonitorInstallPath
	if viper.GetString("debug-monitor-root") != "" {
		monitorInstallPath = viper.GetString("debug-monitor-root")
	}

	cfg.ItemsConfigFile = filepath.Join(
		monitorInstallPath,
		fmt.Sprintf("items-config_%d.yaml", cfg.Port),
	)
	cfg.InteractTimeout = 5 * time.Second
	cfg.DefaultSchedule = "@every 1m"

	b, err := yaml.Marshal(cfg)
	if err != nil {
		return err
	}

	fp := filepath.Join(
		monitorInstallPath,
		fmt.Sprintf("monitor-config_%d.yaml", cfg.Port),
	)

	f, err := os.OpenFile(fp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		return errors.Wrap(err, "open monitor config")
	}
	defer func() {
		_ = f.Close()
	}()

	_, err = f.Write(b)
	if err != nil {
		return err
	}

	cu, _ := user.Current()
	if cu.Uid == "0" {
		_, err = osutil.ExecShellCommand(false, fmt.Sprintf(`chown mysql %s`, fp))
		if err != nil {
			return err
		}
	}
	return nil
}

func generateItemsConfigs() error {
	nginxAddrs := viper.GetStringSlice("nginx-address")
	bkCloudId := viper.GetInt("bk-cloud-id")
	ports := viper.GetIntSlice("port")

	apiCore, err := core.NewCoreWithAddr(int64(bkCloudId), nginxAddrs, core.DefaultRetryOpts...)
	if err != nil {
		return err
	}

	data, err := reversemysqlapi.MonitorItemsConfig(apiCore, ports...)
	if err != nil {
		return err
	}

	itemsConfigs := make(map[string]map[string]*config.MonitorItem)
	err = yaml.Unmarshal(data, &itemsConfigs)
	if err != nil {
		return errors.Wrap(err, "unmarshal items config")
	}

	for port, cfg := range itemsConfigs {
		p, _ := strconv.Atoi(port)
		err := generateOneItemsConfig(p, cfg)
		if err != nil {
			return err
		}
	}
	return nil
}

func generateOneItemsConfig(port int, cfg map[string]*config.MonitorItem) error {
	itemList := maps.Values(cfg)
	slices.SortFunc(itemList, func(a, b *config.MonitorItem) int {
		return strings.Compare(a.Name, b.Name)
	})

	b, err := yaml.Marshal(itemList)
	if err != nil {
		return err
	}

	monitorInstallPath := cst.MySQLMonitorInstallPath
	if viper.GetString("debug-monitor-root") != "" {
		monitorInstallPath = viper.GetString("debug-monitor-root")
	}

	fp := filepath.Join(
		monitorInstallPath,
		fmt.Sprintf("items-config_%d.yaml", port),
	)

	f, err := os.OpenFile(fp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	_, err = f.Write(append(b, '\n'))
	if err != nil {
		return err
	}

	cu, _ := user.Current()
	if cu.Uid == "0" {
		_, err = osutil.ExecShellCommand(false, fmt.Sprintf(`chown mysql %s`, fp))
		if err != nil {
			return err
		}
	}
	return nil
}
