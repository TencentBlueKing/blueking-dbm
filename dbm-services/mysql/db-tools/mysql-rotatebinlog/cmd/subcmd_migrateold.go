package cmd

import (
	"fmt"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
)

var migrateCmd = &cobra.Command{
	Use:          "migrate-old",
	Short:        "migrate old rotate_logbin",
	Long:         `read /home/mysql/rotate_logbin/binlog_task.log`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		configFile := viper.GetString("config")
		comp := rotate.RotateBinlogComp{Config: configFile}
		if err = log.InitLogger(); err != nil {
			return err
		}
		if comp.ConfigObj, err = rotate.InitConfig(configFile); err != nil {
			return err
		}

		if err := models.InitDB(); err != nil {
			return err
		}
		defer models.DB.Conn.Close()
		if err = models.SetupTable(); err != nil {
			return err
		}

		portMap := make(map[int]models.BinlogFileModel)
		for _, inst := range comp.ConfigObj.Servers {
			if _, ok := portMap[inst.Port]; !ok {
				portMap[inst.Port] = models.BinlogFileModel{
					Port:             inst.Port,
					Host:             inst.Host,
					ClusterId:        inst.Tags.ClusterId,
					ClusterDomain:    inst.Tags.ClusterDomain,
					BkBizId:          inst.Tags.BkBizId,
					DBRole:           "",
					BackupStatusInfo: "rotate_logbin",
				}
			}
		}
		if err = rotate.DumpOldFileList(cst.OldRotateDir, portMap); err != nil {
			return err
		} else {
			fmt.Println("success")
		}
		return nil
	},
	PreRun: func(cmd *cobra.Command, args []string) {
	},
}

func init() {
	rootCmd.AddCommand(migrateCmd)
}
