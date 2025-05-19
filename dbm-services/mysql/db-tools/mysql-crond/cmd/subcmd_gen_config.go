package cmd

import (
	"dbm-services/common/reverseapi"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"text/template"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var subCmdGenConfig = &cobra.Command{
	Use:   "gen-config",
	Short: "generate config file for mysql-crond",
	Long:  "generate config file for mysql-crond",
	RunE: func(cmd *cobra.Command, args []string) error {
		t, err := template.New("runtime.yaml").Parse(
			`ip: {{ .IP }}
port: 9999
bk_cloud_id: {{ .BkCloudId }}
bk_monitor_beat:
  custom_event:
    bk_data_id: {{ .EventDataId }}
    access_token: {{ .EventDataToken }}
    report_type: agent
    message_kind: event
  custom_metrics:
    bk_data_id: {{ .MetricsDataId }}
    access_token: {{ .MetricsDataToken }}
    report_type: agent
    message_kind: timeseries
  beat_path: {{ .BeatPath }}
  agent_address: {{ .AgentAddress }}
log:
    console: false
    log_file_dir: {{ .LogPath }}
    debug: false
    source: true
    json: true
pid_path: {{ .PidPath }}
jobs_user: mysql
jobs_config: {{ .InstallPath }}/jobs-config.yaml`,
		)
		if err != nil {
			slog.Error("generate runtime config template", slog.String("err", err.Error()))
			return err
		}

		mysqlCrondInstallPath := cst.MySQLCrondInstallPath
		if viper.GetString("debug-crond-root") != "" {
			mysqlCrondInstallPath = viper.GetString("debug-crond-root")
		}

		fp := filepath.Join(mysqlCrondInstallPath, "runtime.yaml")
		f, err := os.OpenFile(
			fp,
			os.O_CREATE|os.O_TRUNC|os.O_WRONLY,
			0644,
		)
		if err != nil {
			slog.Error("generate runtime config template", slog.String("err", err.Error()))
			return err
		}
		defer func() {
			_ = f.Close()
		}()

		nginxAddrs := viper.GetStringSlice("nginx-address")
		bkCloudId := viper.GetInt("bk-cloud-id")

		rvApi := reverseapi.NewReverseApiWithAddr(int64(bkCloudId), nginxAddrs...)
		data, err := rvApi.MySQL.CrondConfig()
		if err != nil {
			return err
		}

		cfg := struct {
			IP               string `json:"ip"`
			BkCloudId        int    `json:"bk_cloud_id"`
			EventDataId      int    `json:"event_data_id"`
			EventDataToken   string `json:"event_data_token"`
			MetricsDataId    int    `json:"metrics_data_id"`
			MetricsDataToken string `json:"metrics_data_token"`
			LogPath          string `json:"-"`
			PidPath          string `json:"-"`
			InstallPath      string `json:"-"`
			BeatPath         string `json:"beat_path"`
			AgentAddress     string `json:"agent_address"`
		}{}

		err = json.Unmarshal(data, &cfg)
		if err != nil {
			return err
		}
		cfg.LogPath = filepath.Join(mysqlCrondInstallPath, "logs")
		cfg.PidPath = mysqlCrondInstallPath
		cfg.InstallPath = mysqlCrondInstallPath

		err = t.Execute(f, cfg)
		if err != nil {
			slog.Error("generate runtime config template", slog.String("err", err.Error()))
			return err
		}

		cu, _ := user.Current()
		if cu.Uid == "0" {
			err = exec.Command("sh", []string{"-c", fmt.Sprintf("chown mysql %s", fp)}...).Run()
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

	_ = subCmdGenConfig.MarkFlagRequired("nginx-address")
	_ = subCmdGenConfig.MarkFlagRequired("bk-cloud-id")

	// 调试代码
	subCmdGenConfig.PersistentFlags().StringP("debug-ip", "", "", "debug ip")
	subCmdGenConfig.PersistentFlags().StringP("debug-crond-root", "", "", "debug crond-root")

	_ = viper.BindPFlag("nginx-address", subCmdGenConfig.PersistentFlags().Lookup("nginx-address"))
	_ = viper.BindPFlag("bk-cloud-id", subCmdGenConfig.PersistentFlags().Lookup("bk-cloud-id"))

	_ = viper.BindPFlag("debug-ip", subCmdGenConfig.PersistentFlags().Lookup("debug-ip"))
	_ = viper.BindPFlag("debug-crond-root", subCmdGenConfig.PersistentFlags().Lookup("debug-crond-root"))

	rootCmd.AddCommand(subCmdGenConfig)
}
