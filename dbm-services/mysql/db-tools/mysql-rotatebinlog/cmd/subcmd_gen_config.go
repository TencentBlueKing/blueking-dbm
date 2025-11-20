package cmd

import (
	reversemysqlapi "dbm-services/common/reverseapi/apis/mysql"
	"dbm-services/common/reverseapi/pkg/core"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"

	gyaml "github.com/ghodss/yaml"
	"github.com/go-viper/mapstructure/v2"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

type rotateBinlogConfig struct {
	Ip            string        `json:"ip"`
	Port          int           `json:"port"`
	Role          string        `json:"role"`
	BkBizId       int           `json:"bk_biz_id"`
	BkCloudId     int           `json:"bk_cloud_id"`
	ClusterDomain string        `json:"cluster_domain"`
	ClusterId     int           `json:"cluster_id"`
	Configs       rotate.Config `json:"configs"`
	User          string        `json:"user"`
	Password      string        `json:"password"`
}

var subCmdGenConfig = &cobra.Command{
	Use:   "gen-config",
	Short: "generate config file for mysql-rotatebinlog",
	Long:  "generate config file for mysql-rotatebinlog",
	RunE: func(cmd *cobra.Command, args []string) error {
		nginxAddrs := viper.GetStringSlice("nginx-address")
		bkCloudId := viper.GetInt("bk-cloud-id")
		ports := viper.GetIntSlice("port")

		apiCore, err := core.NewCoreWithAddr(int64(bkCloudId), nginxAddrs, core.DefaultRetryOpts...)
		if err != nil {
			return err
		}
		apiCore.SetTimeout(60)

		data, err := reversemysqlapi.RotatebinlogConfig(apiCore, ports...)
		if err != nil {
			return err
		}

		var rotateBinlogConfigs []rotateBinlogConfig
		err = json.Unmarshal(data, &rotateBinlogConfigs)
		if err != nil {
			return err
		}

		for _, ele := range rotateBinlogConfigs {
			err := generateOneInstanceConfig(&ele)
			if err != nil {
				return err
			}

			// 这个生成多次也没啥大问题
			err = generateOneMainConfig(&ele)
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
	subCmdGenConfig.PersistentFlags().StringP("debug-rotatebinlog-root", "", "", "debug rotatebinlog-root")

	_ = viper.BindPFlag("nginx-address", subCmdGenConfig.PersistentFlags().Lookup("nginx-address"))
	_ = viper.BindPFlag("bk-cloud-id", subCmdGenConfig.PersistentFlags().Lookup("bk-cloud-id"))
	_ = viper.BindPFlag("port", subCmdGenConfig.PersistentFlags().Lookup("port"))

	_ = viper.BindPFlag("debug-ip", subCmdGenConfig.PersistentFlags().Lookup("debug-ip"))
	_ = viper.BindPFlag("debug-rotatebinlog-root", subCmdGenConfig.PersistentFlags().Lookup("debug-rotatebinlog-root"))

	rootCmd.AddCommand(subCmdGenConfig)
}

func generateOneInstanceConfig(cfg *rotateBinlogConfig) error {
	serverObj := rotate.ServerObj{
		Host:     cfg.Ip,
		Port:     cfg.Port,
		Username: cfg.User,
		Password: cfg.Password,
		Socket:   "",
		Tags: rotate.InstanceMeta{
			BkBizId:       cfg.BkBizId,
			ClusterDomain: cfg.ClusterDomain,
			ClusterId:     cfg.ClusterId,
			DBRole:        cfg.Role,
		},
	}

	b, err := gyaml.Marshal(serverObj)
	if err != nil {
		return err
	}

	rotateBinlogInstallPath := cst.MysqlRotateBinlogInstallPath
	if viper.GetString("debug-rotatebinlog-root") != "" {
		rotateBinlogInstallPath = viper.GetString("debug-rotatebinlog-root")
	}
	fp := filepath.Join(rotateBinlogInstallPath, fmt.Sprintf("server.%d.yaml", cfg.Port))
	if err := os.WriteFile(fp, b, 0644); err != nil {
		return err
	}
	return nil
}

func generateOneMainConfig(cfg *rotateBinlogConfig) error {
	for k, v := range cfg.Configs.BackupClient {
		if k == "ibs" {
			ibsClient := backup.IBSBackupClient{}
			if reflect.TypeOf(v).Kind() == reflect.Map {
				if err := mapstructure.Decode(v, &ibsClient); err != nil {
					return errors.Wrapf(err, "failed to decode backup_client.ibs values: %v", v)
				} else {
					cfg.Configs.BackupClient[k] = ibsClient
				}
			} else {
				if err := json.Unmarshal([]byte(cast.ToString(v)), &ibsClient); err != nil {
					return errors.Wrapf(err, "failed to decode backup_client.ibs values: %v", v)
				} else {
					cfg.Configs.BackupClient[k] = ibsClient
				}
			}
		} else {
			mapObj := make(map[string]interface{})
			if reflect.TypeOf(v).Kind() == reflect.Map {
				mapObj = v.(map[string]interface{})
			} else if err := json.Unmarshal([]byte(cast.ToString(v)), &mapObj); err != nil {
				return errors.Wrapf(err, "failed to decode backup_client values: %v", v)
			}
			cfg.Configs.BackupClient[k] = mapObj
		}
	}

	cfg.Configs.Servers = nil
	b, err := gyaml.Marshal(cfg.Configs)
	if err != nil {
		return err
	}

	rotateBinlogInstallPath := cst.MysqlRotateBinlogInstallPath
	if viper.GetString("debug-rotatebinlog-root") != "" {
		rotateBinlogInstallPath = viper.GetString("debug-rotatebinlog-root")
	}
	fp := filepath.Join(rotateBinlogInstallPath, "main.yaml")
	if err := os.WriteFile(fp, b, 0644); err != nil {
		return err
	}
	return nil
}
