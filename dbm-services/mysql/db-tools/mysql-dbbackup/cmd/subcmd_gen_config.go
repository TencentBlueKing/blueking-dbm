package cmd

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/common/reverseapi"
	"dbm-services/common/reverseapi/define/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"encoding/json"
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"slices"
	"strings"
	"text/template"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/exp/maps"
)

var subCmdGenConfig = &cobra.Command{
	Use:   "gen-config",
	Short: "generate runtime config for dbbackup",
	Long:  "generate runtime config for dbbackup",
	RunE: func(cmd *cobra.Command, args []string) error {
		nginxAddrs := viper.GetStringSlice("nginx-address")
		bkCloudId := viper.GetInt("bk-cloud-id")
		ports := viper.GetIntSlice("port")

		rvApi := reverseapi.NewReverseApiWithAddr(int64(bkCloudId), nginxAddrs...)
		data, err := rvApi.MySQL.DBBackupConfig(ports...)
		if err != nil {
			return err
		}

		var dbbackupConfigs []mysql.DBBackupConfig
		err = json.Unmarshal(data, &dbbackupConfigs)
		if err != nil {
			return errors.Wrap(err, "failed to unmarshal dbbackup configs")
		}

		for _, ele := range dbbackupConfigs {
			err := generateOneDbbackupConfig(&ele)
			if err != nil {
				return err
			}
		}
		return nil
	},
}

func init() {
	subCmdGenConfig.Flags().StringSliceP("nginx-address", "", nil, "nginx-address")
	subCmdGenConfig.Flags().IntP("bk-cloud-id", "", 0, "bk-cloud-id")
	subCmdGenConfig.Flags().IntSliceP("port", "", nil, "port")
	_ = subCmdGenConfig.MarkFlagRequired("nginx-address")
	_ = subCmdGenConfig.MarkFlagRequired("bk-cloud-id")
	_ = subCmdGenConfig.MarkFlagRequired("port")

	// 调试代码
	subCmdGenConfig.Flags().StringP("debug-ip", "", "", "debug ip")
	subCmdGenConfig.Flags().StringP("debug-dbbackup-root", "", "", "debug dbbackup-root")

	_ = viper.BindPFlag("nginx-address", subCmdGenConfig.Flags().Lookup("nginx-address"))
	_ = viper.BindPFlag("bk-cloud-id", subCmdGenConfig.Flags().Lookup("bk-cloud-id"))
	_ = viper.BindPFlag("port", subCmdGenConfig.Flags().Lookup("port"))

	_ = viper.BindPFlag("debug-ip", subCmdGenConfig.Flags().Lookup("debug-ip"))
	_ = viper.BindPFlag("debug-dbbackup-root", subCmdGenConfig.Flags().Lookup("debug-dbbackup-root"))

	rootCmd.AddCommand(subCmdGenConfig)
}

func generateOneDbbackupConfig(cfg *mysql.DBBackupConfig) error {
	backupOptions, err := generateOneBackupOptions(cfg)
	if err != nil {
		return err
	}

	dsg, err := generateOneDSGString(cfg, backupOptions)
	if err != nil {
		return err
	}

	filter, err := generateOneFilter(backupOptions)
	if err != nil {
		return err
	}

	err = generateOneIniConfig(cfg, backupOptions, dsg, filter)
	if err != nil {
		return err
	}

	return nil
}

func generateOneBackupOptions(cfg *mysql.DBBackupConfig) (*dbbackup.BackupOptions, error) {
	var opt dbbackup.BackupOptions
	err := json.Unmarshal(cfg.Options, &opt)
	if err != nil {
		return nil, err
	}
	return &opt, nil
}

func generateOneFilter(opt *dbbackup.BackupOptions) (*db_table_filter.DbTableFilter, error) {
	var ignoreDbs, ignoreTbls []string

	ignoreDbs = strings.Split(opt.IgnoreObjs.IgnoreDatabases, ",")
	ignoreDbs = append(ignoreDbs, native.DBSys...)
	ignoreDbs = cmutil.StringsRemove(ignoreDbs, native.INFODBA_SCHEMA)

	ignoreTbls = strings.Split(opt.IgnoreObjs.IgnoreTables, ",")

	return db_table_filter.NewFilter([]string{"*"}, []string{"*"}, ignoreDbs, ignoreTbls)
}

func generateOneDSGString(cfg *mysql.DBBackupConfig, opt *dbbackup.BackupOptions) (string, error) {
	switch strings.ToUpper(cfg.Role) {
	case cst.BackupRoleMaster, cst.BackupRoleRepeater, cst.BackupRoleOrphan:
		return opt.Master.DataSchemaGrant, nil
	case cst.BackupRoleSlave:
		return opt.Slave.DataSchemaGrant, nil
	case cst.BackupRoleSpiderMaster, cst.BackupRoleSpiderSlave, cst.BackupRoleSpiderMnt:
		return "schema,grant", nil
	default:
		return "", fmt.Errorf("unknown role %s", cfg.Role)
	}
}

func generateOneIniConfig(cfg *mysql.DBBackupConfig, opt *dbbackup.BackupOptions, dsg string, filter *db_table_filter.DbTableFilter) error {
	iniData := config.BackupConfig{
		Public: config.Public{
			MysqlHost:       cfg.Ip,
			MysqlPort:       cfg.Port,
			MysqlUser:       cfg.User,
			MysqlPasswd:     cfg.Password,
			MysqlRole:       strings.ToLower(cfg.Role),
			BkBizId:         cfg.BkBizId,
			BkCloudId:       cfg.BkCloudId,
			ClusterAddress:  cfg.ImmuteDomain,
			ClusterId:       cfg.ClusterId,
			ShardValue:      cfg.ShardId,
			BackupType:      opt.BackupType,
			DataSchemaGrant: dsg,
		},
		BackupClient: config.BackupClient{},
		LogicalBackup: config.LogicalBackup{
			TableFilter: config.TableFilter{
				Regex: filter.TableFilterRegex(),
			},
		},
		PhysicalBackup: config.PhysicalBackup{
			DefaultsFile: util.GetMyCnfFileName(cfg.Port),
		},
	}

	err := writeIniFile(cfg, &iniData)
	if err != nil {
		return err
	}

	// 中控配置
	if strings.ToLower(cfg.Role) == strings.ToLower(cst.BackupRoleSpiderMaster) {
		tdbCtlPort := mysqlcomm.GetTdbctlPortBySpider(cfg.Port)
		tdbCtlIniData := iniData
		tdbCtlIniData.Public.MysqlPort = tdbCtlPort
		tdbCtlIniData.Public.MysqlRole = cst.BackupRoleTdbctl
		tdbCtlIniData.PhysicalBackup.DefaultsFile = util.GetMyCnfFileName(tdbCtlPort)
		tdbCtlIniData.LogicalBackup.DefaultsFile = filepath.Join(cst.DbbackupGoInstallPath, "mydumper_for_tdbctl.cnf")

		err := writeIniFile(cfg, &tdbCtlIniData)
		if err != nil {
			return err
		}
	}
	return nil
}

func writeIniFile(cfg *mysql.DBBackupConfig, iniData *config.BackupConfig) error {
	buf := new(strings.Builder)

	// 这种别扭的遍历写法是为了保持稳定遍历
	// 这样生成的配置文件diff起来就不会太奇怪
	topKeys := maps.Keys(cfg.ConfigsTemplate)
	slices.Sort(topKeys)

	var encryptOpt = make(map[string]string)
	var encryptOptPrefix = "EncryptOpt"
	for _, k := range topKeys {
		v := cfg.ConfigsTemplate[k]

		_, err := fmt.Fprintf(buf, "[%s]\n", k)
		if err != nil {
			return err
		}

		subKeys := maps.Keys(v)
		slices.Sort(subKeys)
		for _, sk := range subKeys {
			sv := v[sk]
			if strings.HasPrefix(sk, encryptOptPrefix+".") {
				encryptOpt[strings.TrimPrefix(sk, encryptOptPrefix+".")] = sv
				continue
			}
			_, err := fmt.Fprintf(buf, "%s\t=\t%s\n", sk, sv)
			if err != nil {
				return errors.WithMessagef(err, "写配置模版 %s, %s 失败", sk, sv)
			}
		}
		_, _ = fmt.Fprintf(buf, "\n")
	}
	if len(encryptOpt) > 0 {
		_, _ = fmt.Fprintf(buf, "[%s]\n", encryptOptPrefix)
		for k, v := range encryptOpt {
			_, _ = fmt.Fprintf(buf, "%s\t=\t%s\n", k, v)
		}
	}

	tpl, err := template.New("config").Parse(buf.String())
	if err != nil {
		return err
	}

	dbbackupInstallPath := cst.DbbackupGoInstallPath
	if viper.GetString("debug-dbbackup-root") != "" {
		dbbackupInstallPath = viper.GetString("debug-dbbackup-root")
	}
	fp := filepath.Join(dbbackupInstallPath, fmt.Sprintf("dbbackup.%d.ini", iniData.Public.MysqlPort))
	f, err := os.OpenFile(fp, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	err = tpl.Execute(f, iniData)
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
