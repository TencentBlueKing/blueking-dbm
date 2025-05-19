package cmd

import (
	"dbm-services/common/reverseapi"
	"dbm-services/common/reverseapi/define/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/tools"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"encoding/json"
	"fmt"
	"os"
	"os/user"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var subCmdGenConfig = &cobra.Command{
	Use:   "gen-config",
	Short: "generate config for checksum",
	Long:  "generate config for checksum",
	RunE: func(cmd *cobra.Command, args []string) error {
		nginxAddrs := viper.GetStringSlice("nginx-address")
		bkCloudId := viper.GetInt("bk-cloud-id")
		ports := viper.GetIntSlice("port")

		rvApi := reverseapi.NewReverseApiWithAddr(int64(bkCloudId), nginxAddrs...)
		data, err := rvApi.MySQL.ChecksumConfig(ports...)
		if err != nil {
			return err
		}

		var checksumConfigs []mysql.ChecksumConfig

		err = json.Unmarshal(data, &checksumConfigs)
		if err != nil {
			return err
		}

		for _, cfg := range checksumConfigs {
			err := generateOneRuntimeConfig(&cfg)
			if err != nil {
				return err
			}
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
	subCmdGenConfig.PersistentFlags().StringP("debug-checksum-root", "", "", "debug checksum-root")
	subCmdGenConfig.PersistentFlags().StringP("debug-pt-path", "", "", "debug pt-path")

	_ = viper.BindPFlag("nginx-address", subCmdGenConfig.PersistentFlags().Lookup("nginx-address"))
	_ = viper.BindPFlag("bk-cloud-id", subCmdGenConfig.PersistentFlags().Lookup("bk-cloud-id"))
	_ = viper.BindPFlag("port", subCmdGenConfig.PersistentFlags().Lookup("port"))

	_ = viper.BindPFlag("debug-ip", subCmdGenConfig.PersistentFlags().Lookup("debug-ip"))
	_ = viper.BindPFlag("debug-checksum-root", subCmdGenConfig.PersistentFlags().Lookup("debug-checksum-root"))
	_ = viper.BindPFlag("debug-pt-path", subCmdGenConfig.PersistentFlags().Lookup("debug-pt-path"))

	rootCmd.AddCommand(subCmdGenConfig)
}

func generateOneRuntimeConfig(cfg *mysql.ChecksumConfig) error {
	checksumInstallPath := cst.ChecksumInstallPath
	if viper.GetString("debug-checksum-root") != "" {
		checksumInstallPath = viper.GetString("debug-checksum-root")
	}

	logDir := filepath.Join(checksumInstallPath, "logs")
	tl := tools.NewToolSetWithPickNoValidate(tools.ToolMysqlTableChecksum, tools.ToolPtTableChecksum)

	var ptChecksumPath string
	if viper.GetString("debug-pt-path") != "" {
		ptChecksumPath = viper.GetString("debug-pt-path")
	} else {
		ptChecksumPath = tl.MustGet(tools.ToolPtTableChecksum)
	}

	var ignoreDbs []string
	ignoreDbs = append(ignoreDbs, cfg.SystemDbs...)
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%s%%`, cfg.StageDBHeader))
	ignoreDbs = append(ignoreDbs, `bak_%`) // gcs/scr truncate header
	ignoreDbs = append(ignoreDbs, fmt.Sprintf(`%%%s`, cfg.RollbackDBTail))

	rcfg := config.Config{
		BkBizId: cfg.BkBizId,
		Cluster: config.Cluster{
			Id:           cfg.ClusterId,
			ImmuteDomain: cfg.ImmuteDomain,
		},
		Host: config.Host{
			Ip:       cfg.IP,
			Port:     cfg.Port,
			User:     cfg.User,
			Password: cfg.Password,
		},
		InnerRole:  config.InnerRoleEnum(cfg.Role),
		ReportPath: filepath.Join(cst.DBAReportBase, "checksum"),
		Slaves:     nil,
		Filter:     config.Filter{},
		PtChecksum: config.PtChecksum{
			Path:     ptChecksumPath,
			Switches: []string{},
			Args: []map[string]interface{}{
				{
					"name":  "run-time",
					"value": fmt.Sprintf("%dh", 2),
				},
			},
			Replicate: fmt.Sprintf("%s.checksum", native.INFODBA_SCHEMA),
		},
		Log: &config.LogConfig{
			Console:    false,
			LogFileDir: &logDir,
			Debug:      false,
			Source:     true,
			Json:       true,
		},
		Schedule: cfg.Schedule,
		ApiUrl:   cfg.ApiUrl,
	}

	rcfg.SetFilter(nil, ignoreDbs, nil, nil)

	b, err := yaml.Marshal(rcfg)
	if err != nil {
		return err
	}

	fp := filepath.Join(checksumInstallPath, fmt.Sprintf("checksum_%d.yaml", cfg.Port))
	f, err := os.OpenFile(
		fp,
		os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
		0644,
	)
	if err != nil {
		return err
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
