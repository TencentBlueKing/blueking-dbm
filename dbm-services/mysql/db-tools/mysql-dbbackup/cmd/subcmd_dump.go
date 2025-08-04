// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"bytes"
	"context"
	"encoding/json"
	errs "errors"
	"fmt"
	"log"
	"os"
	"path"
	"path/filepath"
	"strings"
	"syscall"
	"text/template"
	"time"

	reapi "dbm-services/common/reverseapi/apis/common"
	recore "dbm-services/common/reverseapi/pkg/core"

	sshgo "github.com/melbahja/goph"
	"github.com/pkg/errors"
	"github.com/spf13/cast"
	"github.com/spf13/viper"
	"golang.org/x/crypto/ssh"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/assets"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/precheck"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

func init() {
	dumpCmd.PersistentFlags().StringP("backup-type", "t", cst.BackupTypeAuto, "overwrite Public.BackupType")
	_ = viper.BindPFlag("Public.BackupType", dumpCmd.PersistentFlags().Lookup("backup-type"))

	dumpCmd.PersistentFlags().String("backup-id", "", "overwrite Public.BackupId")
	dumpCmd.PersistentFlags().String("bill-id", "", "overwrite Public.BillId")
	dumpCmd.PersistentFlags().Int("shard-value", -1, "overwrite Public.ShardValue")
	dumpCmd.PersistentFlags().Bool("nocheck-diskspace", false, "overwrite Public.NoCheckDiskSpace")
	dumpCmd.PersistentFlags().String("enable-backup-client", "auto",
		"enable backup-client, auto means check if this machine is standby role")
	dumpCmd.PersistentFlags().String("backup-file-tag", "", "overwrite BackupClient.FileTag")
	dumpCmd.PersistentFlags().String("backup-to-remote", "", "backup to remote using ssh with netcat, "+
		"format: ssh://user:pass@remote_host:remote_port//data/dbbak")
	_ = viper.BindPFlag("Public.BackupId", dumpCmd.PersistentFlags().Lookup("backup-id"))
	_ = viper.BindPFlag("Public.BillId", dumpCmd.PersistentFlags().Lookup("bill-id"))
	_ = viper.BindPFlag("Public.ShardValue", dumpCmd.PersistentFlags().Lookup("shard-value"))
	_ = viper.BindPFlag("Public.NoCheckDiskSpace", dumpCmd.PersistentFlags().Lookup("nocheck-diskspace"))
	_ = viper.BindPFlag("BackupClient.EnableBackupClient", dumpCmd.PersistentFlags().Lookup("backup-client"))
	_ = viper.BindPFlag("BackupClient.FileTag", dumpCmd.PersistentFlags().Lookup("backup-file-tag"))

	dumpCmd.PersistentFlags().String("backup-dir", "/data/dbbak",
		"backup root path to save, overwrite Public.BackupDir")
	dumpCmd.PersistentFlags().String("cluster-domain", "",
		"cluster domain to report, overwrite Public.ClusterAddress")
	dumpCmd.PersistentFlags().StringP("data-schema-grant", "g", "",
		"all|schema|data|grant, overwrite Public.DataSchemaGrant")
	dumpCmd.PersistentFlags().Int("is-full-backup", 0,
		"report backup-id as full backup. default 0 means auto judge by backup-type,data-schema-grant")

	viper.BindPFlag("Public.BackupDir", dumpCmd.PersistentFlags().Lookup("backup-dir"))
	viper.BindPFlag("Public.ClusterAddress", dumpCmd.PersistentFlags().Lookup("cluster-domain"))
	viper.BindPFlag("Public.DataSchemaGrant", dumpCmd.PersistentFlags().Lookup("data-schema-grant"))
	viper.BindPFlag("Public.IsFullBackup", dumpCmd.PersistentFlags().Lookup("is-full-backup"))

	// Connection Options
	dumpCmd.PersistentFlags().StringP("host", "h", "", "The host to connect to, overwrite Public.MysqlHost")
	dumpCmd.PersistentFlags().IntP("port", "P", 3306, "TCP/IP port to connect to, overwrite Public.MysqlPort")
	dumpCmd.PersistentFlags().StringP("user", "u", "", "Username with the necessary privileges, "+
		"overwrite Public.MysqlUser")
	dumpCmd.PersistentFlags().StringP("password", "p", "", "User password, overwrite Public.MysqlPasswd")
	viper.BindPFlag("Public.MysqlHost", dumpCmd.PersistentFlags().Lookup("host"))
	viper.BindPFlag("Public.MysqlPort", dumpCmd.PersistentFlags().Lookup("port"))
	viper.BindPFlag("Public.MysqlUser", dumpCmd.PersistentFlags().Lookup("user"))
	viper.BindPFlag("Public.MysqlPasswd", dumpCmd.PersistentFlags().Lookup("password"))

	dumpCmd.PersistentFlags().StringSliceP("config", "c",
		[]string{}, "config files to backup, comma separated. (required)")
	_ = dumpCmd.MarkFlagRequired("config")

	dumpCmd.AddCommand(dumpLogicalCmd)
}

type backupTask struct {
	backupId      string
	backupConfig  *config.BackupConfig
	logReport     *dbareport.BackupLogReport
	indexFilePath string
	statusReport  *dbareport.MysqlBackupStatusEvent
	//SshClient    *sshgo.Client
}

func newBackupTask(backupId string) *backupTask {
	if backupId == "" {
		backupId, _ = dbareport.GenerateUUid()
	}
	return &backupTask{
		backupId: backupId,
	}
}

var dumpCmd = &cobra.Command{
	Use:          "dumpbackup",
	Short:        "Run backup",
	Long:         `Run backup using config, include logical and physical`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql:mysql", cst.DbbackupGoInstallPath)
		}()
		exePath, err := os.Executable()
		if err != nil {
			return err
		}
		backupexe.ExecuteHome = filepath.Dir(exePath)
		if err = dumpExecute(cmd, args); err != nil {
			logger.Log.Error("dumpbackup failed ", err.Error())
			manager := ma.NewManager(cst.MysqlCrondUrl)
			body := struct {
				Name      string
				Content   string
				Dimension map[string]interface{}
			}{}
			body.Name = "dbbackup-by-host"
			body.Content = fmt.Sprintf("run dbbackup failed %s", err.Error())
			body.Dimension = map[string]interface{}{}
			if sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension); sendErr != nil {
				logger.Log.Error("SendEvent failed", sendErr.Error())
			}
			return err
		}
		return nil
	},
}

func dumpExecute(cmd *cobra.Command, args []string) (err error) {
	manager := ma.NewManager(cst.MysqlCrondUrl)
	body := struct {
		Name      string
		Content   string
		Dimension map[string]interface{}
	}{}
	body.Name = "dbbackup"
	//body.Content = fmt.Sprintf("%s。单据号：%s", "分区任务执行失败", e.Params.Ticket)
	body.Dimension = make(map[string]interface{})
	if err = logger.InitLog("dbbackup_dump.log"); err != nil {
		return err
	}
	cnfFiles, _ := cmd.PersistentFlags().GetStringSlice("config") // PersistentFlags global flags
	if len(cnfFiles) == 0 {
		if cnfFiles, err = filepath.Glob("dbbackup.*.ini"); err != nil {
			return err
		} else if len(cnfFiles) == 0 {
			return errors.New("no dbbackup.*.ini found")
		}
	}
	logger.Log.Infof("using config files: %v", cnfFiles)
	remoteConfig := &config.SSHConfig{}
	if backupToRemote, err := cmd.PersistentFlags().GetString("backup-to-remote"); backupToRemote != "" {
		if remoteConfig, err = config.ParseSshDsn(backupToRemote); err != nil {
			return err
		}
	}
	var errList error
	for _, f := range cnfFiles {
		task := newBackupTask("")
		config.SetDefaults()
		var cnf = config.BackupConfig{}
		if err := initConfig(f, &cnf, logger.Log); err != nil {
			errList = errs.Join(errList, errors.WithMessagef(err, "init failed for %d", cnf.Public.MysqlPort))
			logger.Log.Error("Create Dbbackup: fail to parse ", f)
			// 配置初始化失败了，sync report 目前无法上报!!!
			continue
		}
		if cnf.Public.BackupId != "" {
			task.backupId = cnf.Public.BackupId // 使用传入的 backup_id 覆盖临时生成的 id
		}
		if cnf.Public.BackupId == "" {
			cnf.Public.BackupId = task.backupId
		}
		task.statusReport = dbareport.NewMysqlBackupStatusEvent(&cnf)
		reportCore, err := recore.NewCore(0, recore.DefaultRetryOpts...)
		if err != nil {
			logger.Log.Error("report NewCore failed", err.Error()) // reportCore is nil
		}

		body.Dimension["bk_biz_id"] = cnf.Public.BkBizId
		body.Dimension["cluster_id"] = cnf.Public.ClusterId
		body.Dimension["cluster_domain"] = cnf.Public.ClusterAddress
		body.Dimension["instance"] = fmt.Sprintf("%s:%d", cnf.Public.MysqlHost, cnf.Public.MysqlPort)

		if remoteConfig.EnableRemote {
			cnf.BackupToRemote = *remoteConfig
		}
		cnf.SetConfigFilePath(f) // 给 remote backup 用的

		var maxTimeoutSeconds int64 = 10 * 24 * 86400 // 最大允许单个备份任务跑 10 天
		if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleMaster && cnf.Public.BackupTimeOut != "" {
			maxTimeoutSeconds, err = util.GetMaxRunningTime(cnf.Public.BackupTimeOut)
			if err != nil {
				errList = errs.Join(errList, err)
				continue
			}
		}
		if maxTimeoutSeconds < 5 { // +5 seconds
			errList = errs.Join(errList, errors.Errorf("do not start backup %d, because of too short timeout %s",
				cnf.Public.MysqlPort, cnf.Public.BackupTimeOut))
			continue
		}
		ctx := context.Background()
		done := make(chan error, 1)
		go func() {
			err := task.backupData(ctx, &cnf)
			if err != nil {
				logger.Log.Error("Create Dbbackup: Failure for ", f)
			}
			done <- err
		}()

		select {
		case doneErr := <-done:
			if doneErr != nil {
				if resp, err := reapi.SyncReport(reportCore,
					task.statusReport.SetStatus("Failed", doneErr.Error())); err != nil {
					logger.Log.Warnf("report backup status, resp: err=%s, resp=%s", err, string(resp))
				}
				body.Content = fmt.Sprintf("run dbbackup failed for %s, err=%s", f, doneErr.Error())
				if sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension); sendErr != nil {
					logger.Log.Error("SendEvent failed for ", f, sendErr.Error())
				}
				errList = errs.Join(errList, doneErr)
			}
			continue
		case <-time.After(time.Duration(maxTimeoutSeconds) * time.Second):
			doneErr := fmt.Errorf("backup timeout exceed %s for port %d",
				cnf.Public.BackupTimeOut, cnf.Public.MysqlPort)
			if resp, err := reapi.SyncReport(reportCore,
				task.statusReport.SetStatus("Failed", doneErr.Error())); err != nil {
				logger.Log.Warnf("report backup status, resp: err=%s, resp=%s", err, string(resp))
			}
			body.Content = fmt.Sprintf("run dbbackup failed for %s, error=%s", f, doneErr.Error())
			if sendErr := manager.SendEvent(body.Name, body.Content, body.Dimension); sendErr != nil {
				logger.Log.Error("SendEvent failed for ", f, sendErr.Error())
			}
			errList = errs.Join(errList, doneErr)
			time.Sleep(cst.KillDelayMilliSec * time.Millisecond)
			syscall.Kill(os.Getpid(), syscall.SIGINT) // 确保子进程能够获取到中断信号
			continue                                  //break  // 同一批发起的备份任务，某个任务超时，后续任务也不进行
		}
	}
	if errList != nil {
		return errList
	}
	return nil
}

func (t *backupTask) backupData(ctx context.Context, cnf *config.BackupConfig) (err error) {
	logger.Log.Infof("Dbbackup begin for %d", cnf.Public.MysqlPort)
	// validate dumpBackup
	if err = validate.GoValidateStructTag(cnf.Public, "ini"); err != nil {
		return err
	}
	if cnf.Public.EncryptOpt == nil {
		cnf.Public.EncryptOpt = &cmutil.EncryptOpt{EncryptEnable: false}
	}
	encOpt := cnf.Public.EncryptOpt
	if encOpt.EncryptEnable {
		if encOpt.EncryptCmd == "xbcrypt" {
			encOpt.EncryptCmd = filepath.Join(backupexe.ExecuteHome, "bin/xbcrypt")
		}
		if err := encOpt.Init(); err != nil {
			return errors.Wrap(err, "fail to init crypt tool")
		}
		cnf.Public.EncryptOpt = encOpt
	}

	logReport, err := dbareport.NewBackupLogReport(cnf)
	if err != nil {
		return err
	}
	// 初始化 reportLogger，后续可通过 dbareport.Report 来调用
	if err = dbareport.InitReporter(cnf.Public.ReportPath); err != nil {
		return err
	}
	reportCore, err := recore.NewCore(0, recore.DefaultRetryOpts...)
	if err != nil {
		logger.Log.Error("report NewCore failed", err.Error()) // reportCore is nil
	}
	if resp, reportErr := reapi.SyncReport(reportCore, t.statusReport.SetStatus("Begin", "")); reportErr != nil {
		logger.Log.Warnf("report backup status, resp: %s", string(resp))
	}
	logger.Log.Info("parse config file: end")
	if cnf.Public.DataSchemaGrant == cst.BackupNone {
		logger.Log.Infof("backup nothing for %d, exit", cnf.Public.MysqlPort)
		return nil
	}
	if err := precheck.BeforeDump(ctx, cnf); err != nil {
		return err
	}
	// 备份权限 backup priv info
	// 注意：如果只备份权限，则走 backupexe.ExecuteBackup(cnf) 逻辑
	//  如果还备份 schema/data，则走下面这个逻辑
	if cnf.Public.IfBackupGrant() && !cnf.Public.IfBackupGrantOnly() {
		logger.Log.Infof("backup grant for %d: begin", cnf.Public.MysqlPort)
		if err := backupexe.BackupGrant(&cnf.Public); err != nil {
			logger.Log.Error("Failed to backup Grant information")
			return err
		}
		logger.Log.Info("backup Grant information: end")
	}
	if cnf.BackupToRemote.EnableRemote && !cnf.Public.IfBackupData() {
		err = errors.Errorf("backup-to-remote=true only works with DataSchemaGrant include data")
		logger.Log.Warnf("%s. set EnableRemote=false", err.Error())
		return err
	}
	if cnf.BackupToRemote.EnableRemote && cnf.Public.BackupType != cst.BackupPhysical {
		return errors.Errorf("backup stream to remote only support physical but got %s for port=%d",
			cnf.Public.BackupType, cnf.Public.MysqlPort)
	}
	// long_slow_query
	// check slave status

	// execute backup
	if resp, reportErr := reapi.SyncReport(reportCore, t.statusReport.SetStatus("Running", "")); reportErr != nil {
		logger.Log.Warnf("report backup status, resp: %s", string(resp))
	}
	var sshClient *sshgo.Client
	if cnf.BackupToRemote.EnableRemote {
		if sshClient, err = initSshClient(cnf); err != nil {
			return err
		}
		defer sshClient.Close()
	}
	if cnf.BackupToRemote.EnableRemote {
		if err = prepareBackupToRemote(cnf, sshClient); err != nil {
			return err
		}
	}
	// ExecuteBackup 执行备份后，返回备份元数据信息
	logger.Log.Info("backup main run:", cnf.Public.MysqlPort)
	metaInfo, exeErr := backupexe.ExecuteBackup(ctx, cnf)
	if exeErr != nil {
		return exeErr
	}
	indexFilePath := path.Join(cnf.Public.BackupDir, cnf.Public.TargetName()+".index")
	err = metaInfo.SaveIndexContent(indexFilePath)
	if err != nil {
		return err
	}
	logger.Log.Info("backup main finish:", cnf.Public.MysqlPort, indexFilePath)

	if resp, reportErr := reapi.SyncReport(reportCore, t.statusReport.SetStatus("Tarball", "")); reportErr != nil {
		logger.Log.Warnf("report backup status, resp: %s", string(resp))
	}
	if cnf.BackupToRemote.EnableRemote {
		if err = t.runBackupToRemote(cnf, indexFilePath, logReport, sshClient); err != nil {
			return err
		}
	} else {
		if err = backupTarAndUpload(cnf, indexFilePath, logReport); err != nil {
			logger.Log.Error("Failed to tar and upload, error: ", err)
			return err
		}
	}
	fmt.Printf("backup_index_file:%s\n", indexFilePath)
	if resp, reportErr := reapi.SyncReport(reportCore, t.statusReport.SetStatus("Success", "")); reportErr != nil {
		logger.Log.Warnf("report backup status, resp: %s", string(resp))
	}
	logger.Log.Infof("Dbbackup Success for %d", cnf.Public.MysqlPort)
	return nil
}

func initSshClient(cnf *config.BackupConfig) (sshClient *sshgo.Client, err error) {
	// 备份到远程时，关闭本地磁盘空间检查
	cnf.Public.NoCheckDiskSpace = true
	logger.Log.Infof("Save backup to remote: %s:%d %s",
		cnf.BackupToRemote.SshHost, cnf.BackupToRemote.SshPort, cnf.BackupToRemote.SaveDir)
	// write metaInfo to draft file
	var sshAuth sshgo.Auth
	if cnf.BackupToRemote.SshPrivateKey != "" {
		sshAuth, err = sshgo.Key(cnf.BackupToRemote.SshPrivateKey, "")
		if err != nil {
			return nil, err
		}
	} else {
		sshAuth = sshgo.KeyboardInteractive(cnf.BackupToRemote.SshPass)
	}
	sshClient, err = sshgo.NewConn(&sshgo.Config{
		User:     cnf.BackupToRemote.SshUser,
		Addr:     cnf.BackupToRemote.SshHost,
		Port:     uint(cnf.BackupToRemote.SshPort),
		Auth:     sshAuth,
		Timeout:  5 * time.Second,
		Callback: ssh.InsecureIgnoreHostKey(),
	})
	if err != nil {
		return nil, err
	}
	return sshClient, nil
}

func prepareBackupToRemote(cnf *config.BackupConfig, sshClient *sshgo.Client) (err error) {
	if cnf.BackupToRemote.NcPort == 0 {
		cnf.BackupToRemote.NcPort = cnf.Public.MysqlPort + 100
	}
	param := map[string]string{
		"dbbackupHome": backupexe.ExecuteHome,
	}
	tpl, err := template.ParseFS(assets.TemplateFS, "nc_starter.sh.tmpl")
	if err != nil {
		return err
	}
	ncStarterScriptName := filepath.Join(cnf.Public.BackupDir,
		fmt.Sprintf("nc_starter_%s_%d.sh", cnf.Public.MysqlHost, cnf.Public.MysqlPort))
	f, err := os.OpenFile(ncStarterScriptName, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0755)
	if err != nil {
		return err
	}
	if err = tpl.Execute(f, param); err != nil {
		return err
	}
	f.Close()

	//  nc | xbstream 在脚本里是放后台执行的
	remoteNcStarterScriptName := filepath.Join(cnf.BackupToRemote.SaveDir, filepath.Base(ncStarterScriptName))
	if err = sshClient.Upload(ncStarterScriptName, remoteNcStarterScriptName); err != nil {
		return err
	}
	// 如果目标机器 dbbackup-go 介质不存在，传输过去
	remoteDbbackupHome := backupexe.ExecuteHome + "-remote" // /home/mysql/dbbackup-go-remote
	remoteDbbackupBin := filepath.Join(remoteDbbackupHome, "dbbackup")
	if output, err := sshClient.Run("ls " + remoteDbbackupBin); err != nil {
		if !strings.Contains(string(output), "No such file or directory") {
			return errors.WithMessagef(err, "check bin exists %s, output: %s", remoteDbbackupBin, string(output))
		}
		logger.Log.Infof("dbbackup not found, try to send it to remote")
		// 打包下发 /home/mysql/dbbackup-go
		mysqlHome := filepath.Dir(backupexe.ExecuteHome) // /home/mysql
		dbbackupPkg := filepath.Join(mysqlHome, "dbbackup-go.tar.gz")
		sendDbbackup := []string{"tar", "-zcf", dbbackupPkg, "dbbackup-go", "--exclude", "dbbackup-go/logs"}
		if _, _, err = cmutil.ExecCommand(false, mysqlHome, sendDbbackup[0], sendDbbackup[1:]...); err != nil {
			return errors.WithMessage(err, "tar dbbackup-go.tar.gz failed")
		}
		if err = sshClient.Upload(dbbackupPkg, dbbackupPkg); err != nil {
			return err
		}
		untarDbbackup := fmt.Sprintf("tar -zxf %s -C %s", dbbackupPkg, cnf.BackupToRemote.SaveDir)
		if output, err = sshClient.Run(untarDbbackup); err != nil {
			return errors.WithMessagef(err, "untar dbbackup-go.tar.gz failed, output: %s", string(output))
		}
		renameDbbackup := fmt.Sprintf("mv %s %s; rm -f %s",
			filepath.Join(cnf.BackupToRemote.SaveDir, "dbbackup-go"), remoteDbbackupHome, dbbackupPkg)
		if output, err = sshClient.Run(fmt.Sprintf("bash -c '%s'", renameDbbackup)); err != nil {
			return errors.WithMessagef(err, "rename to dbbackup-go-remote failed, output: %s", string(output))
		}
		if output, err = sshClient.Run("ls " + remoteDbbackupBin); err != nil {
			return errors.WithMessagef(err, "check bin exists %s, output: %s", remoteDbbackupBin, string(output))
		}
	} else {
		// 如果目标机器 dbbackup-go 存在，只更新 dbbackup bin
		if err = sshClient.Upload(filepath.Join(backupexe.ExecuteHome, "dbbackup"), remoteDbbackupBin); err != nil {
			return err
		}
	}

	remoteTargetDir := filepath.Join(cnf.BackupToRemote.SaveDir, cnf.Public.TargetName())
	//ncCmd := []string{"nc 6666 -l", "|", "xbstream -x -C /data/dbbak/backup_20000/"}
	//logger.Log.Info("nc start: ", strings.Join(ncRecvs, " "))

	bashNc := []string{remoteNcStarterScriptName,
		cnf.BackupToRemote.SshHost, cast.ToString(cnf.BackupToRemote.NcPort), remoteTargetDir}
	logger.Log.Infof("nc start: %s", strings.Join(bashNc, " "))
	go func() {
		// 这里测试出一个现象，sshClient.Run 脚本里的命令带 & 后台执行，会阻塞整个脚本，所以用 go func() + time.Sleep 解决
		if output, err := sshClient.Run(strings.Join(bashNc, " ")); err != nil {
			if strings.Contains(string(output), "Address already in use") {
				// 换个端口重试一下
				cnf.BackupToRemote.NcPort += 10
				bashNc = []string{remoteNcStarterScriptName,
					cnf.BackupToRemote.SshHost, cast.ToString(cnf.BackupToRemote.NcPort), remoteTargetDir}
				logger.Log.Infof("port already in use, nc start-retry: %s", strings.Join(bashNc, " "))
				if output, err := sshClient.Run(strings.Join(bashNc, " ")); err != nil {
					msg := fmt.Sprintf("nc start failed output:%s, cmd:%s", string(output), strings.Join(bashNc, " "))
					logger.Log.Error(err.Error(), msg)
					log.Fatalf(err.Error(), msg)
					//return errors.WithMessage(err, msg)
				} else {
					logger.Log.Infof("nc start %d success", cnf.BackupToRemote.NcPort)
				}
			} else {
				msg := fmt.Sprintf("nc bind failed output:%s, cmd:%s", string(output), strings.Join(bashNc, " "))
				logger.Log.Error(err.Error(), msg)
				log.Fatalf(err.Error(), msg)
				//return errors.WithMessage(err, msg)
			}
		} else {
			logger.Log.Infof("nc start %d success", cnf.BackupToRemote.NcPort)
		}
	}()
	time.Sleep(2 * time.Second)
	return nil
}

// runBackupToRemote 上远程机器打包
func (t *backupTask) runBackupToRemote(cnf *config.BackupConfig, indexFilePath string,
	logReport *dbareport.BackupLogReport, sshClient *sshgo.Client) (err error) {
	remoteIndexFile := filepath.Join(cnf.BackupToRemote.SaveDir, filepath.Base(indexFilePath))
	var remoteConfigFile string
	// 上传 index file, priv file, config file
	if err = sshClient.Upload(indexFilePath, remoteIndexFile); err != nil {
		return err
	}
	oldIndexFileMd5, err := cmutil.GetFileMd5(indexFilePath)
	if err != nil {
		return err
	}

	privFilePath := path.Join(cnf.Public.BackupDir, cnf.Public.TargetName()+".priv")
	if cmutil.FileExists(privFilePath) {
		remotePrivFile := filepath.Join(cnf.BackupToRemote.SaveDir, filepath.Base(privFilePath))
		if err = sshClient.Upload(privFilePath, remotePrivFile); err != nil {
			return err
		}
	}
	if configFilePath := cnf.GetConfigFilePath(); configFilePath != "" {
		remoteConfigFile = filepath.Join(cnf.BackupToRemote.SaveDir,
			fmt.Sprintf("dbbackup.%s_%d.ini", cnf.Public.MysqlHost, cnf.Public.MysqlPort))
		if err = sshClient.Upload(configFilePath, remoteConfigFile); err != nil {
			return err
		}
	} else {
		return errors.Errorf("config file path is empty")
	}

	// tar and split by remote
	remoteDbbackupBin := filepath.Join(backupexe.ExecuteHome+"-remote", "dbbackup")
	remoteCmd, _ := sshClient.Command(remoteDbbackupBin, "tar-upload",
		"--config", remoteConfigFile,
		"--backup-index-file", remoteIndexFile,
		"--with-remote-enabled")
	logger.Log.Infof("run command in remote:%s ", remoteCmd.String())
	var cmdErr bytes.Buffer
	remoteCmd.Stderr = &cmdErr
	if err = remoteCmd.Run(); err != nil {
		return errors.WithMessagef(err, cmdErr.String())
	}

	// .index.remote 里面肯定会补充备份文件列表
	if err = sshClient.Download(remoteIndexFile+".remote", indexFilePath); err != nil {
		return errors.WithMessagef(err, "download remote index file failed:%s", remoteIndexFile+".remote")
	}
	newIndexFileMd5, err := cmutil.GetFileMd5(indexFilePath)
	if err != nil {
		return err
	}
	if oldIndexFileMd5 == newIndexFileMd5 {
		return errors.Errorf("index file %s md5 expect to be changed by remote, please check", indexFilePath)
	}
	if err = logReport.ReportBackupResult(indexFilePath, false, false); err != nil {
		logger.Log.Error("failed to report backup result, err: ", err)
		return err
	}
	// 备份文件被传输到远程，不调用 ReportToLocalBackup
	return nil
}

func backupTarAndUpload(
	cnf *config.BackupConfig,
	indexFilePath string,
	logReport *dbareport.BackupLogReport) (err error) {

	metaInfo := &dbareport.IndexContent{}
	if buf, err := os.ReadFile(indexFilePath); err != nil {
		return err
	} else {
		if err = json.Unmarshal(buf, metaInfo); err != nil {
			return errors.WithMessagef(err, "unmarshal metaInfo %s", indexFilePath)
		}
	}
	targetDirName := strings.TrimSuffix(filepath.Base(indexFilePath), ".index")
	targetDir := path.Join(cnf.Public.BackupDir, targetDirName)
	cnf.Public.SetTargetName(targetDirName)
	cnf.Public.BackupDir = filepath.Dir(indexFilePath)
	cnf.Public.BackupType = metaInfo.BackupType // this is real backup type
	cnf.Public.DataSchemaGrant = metaInfo.DataSchemaGrant

	// build regex used for package
	if err = logReport.BuildMetaInfo(cnf, metaInfo); err != nil {
		return err
	}

	// 如果 index 里面的文件列表全都存在，说明已经完成了打包切分，不需要再执行 PackageBackupFiles
	alreadyTarballed := false
	if cnf.Public.IfBackupGrantOnly() && !cnf.BackupToRemote.EnableRemote {
		alreadyTarballed = true
		metaInfo.AddPrivFileItem(targetDir)
		if err = metaInfo.SaveIndexContent(indexFilePath); err != nil {
			return err
		}
	} else if len(metaInfo.FileList) == 0 {
		alreadyTarballed = false
	} else {
		for _, tarFile := range metaInfo.FileList {
			if tarFile.FileType == cst.FilePriv || tarFile.FileType == cst.FileIndex {
				continue
			}
			// 如果已经存在 tar file，我们认为已经打包过了. 但我们也要检查tar文件是否还存在本地
			alreadyTarballed = true
			if f := filepath.Join(cnf.Public.BackupDir, tarFile.FileName); !cmutil.FileExists(f) {
				return errors.Errorf("file not exists %s from index file", f)
			}
		}
	}
	if !alreadyTarballed {
		// PackageBackupFiles 会把打包后的文件信息，更新到 metaInfo
		logger.Log.Infof("start to tar files, Index BackupMetaInfo:%+v", metaInfo)
		_, tarErr := backupexe.PackageBackupFiles(cnf, metaInfo)
		if tarErr != nil {
			logger.Log.Error("Failed to tar the backup file, error: ", tarErr)
			return tarErr
		}
	}
	// 只有 standby 实例 才需要上报（非 standby 默认是不 report, 不 upload）
	if cnf.BackupClient.EnableBackupClient == "yes" {
		// run backup_client
		if err = logReport.ReportBackupResult(indexFilePath, true, true); err != nil {
			logger.Log.Error("failed to report backup result, err: ", err)
			return err
		}
	}
	if err = logReport.ReportToLocalBackup(indexFilePath); err != nil {
		logger.Log.Warnf("failed to write %d local_backup_report, err: %s. ignore", metaInfo.BackupPort, err)
		// return err
	}

	logger.Log.Info("report backup info: end")
	return nil
}
