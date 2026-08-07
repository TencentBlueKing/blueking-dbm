/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmd

import (
	"fmt"
	"sort"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

func init() {
	removeBackupsCmd.Flags().IntSlice("port", nil,
		"port list to remove backups, comma separated. If not given, remove backups for all ports")
	removeBackupsCmd.Flags().String("size-to-free", "",
		"expect disk size to be freed. format like 200g, 2048m")
	removeBackupsCmd.Flags().Float64("max-disk-used-pct", 0,
		"expect backup disk usage percent to be below this value, e.g. 80 means 80%")

	rootCmd.AddCommand(removeBackupsCmd)
}

var removeBackupsCmd = &cobra.Command{
	Use:   "remove_backups",
	Short: "remove local backup files to free disk space",
	Long: `remove local backup files to free disk space.
Priority: remove oldest backups first across all ports.
For example, if there are 2 ports each with 3 days of backups,
it will first remove day-3 backups for all ports, then day-2, etc.`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := logger.InitLog("dbbackup_remove.log"); err != nil {
			return err
		}

		ports, _ := cmd.Flags().GetIntSlice("port")
		sizeToFreeStr, _ := cmd.Flags().GetString("size-to-free")
		maxDiskUsedPct, _ := cmd.Flags().GetFloat64("max-disk-used-pct")

		if sizeToFreeStr == "" && maxDiskUsedPct == 0 {
			return errors.New("please provide at least one of --size-to-free or --max-disk-used-pct")
		}

		// 解析 size-to-free
		var sizeToFree int64
		if sizeToFreeStr != "" {
			var err error
			sizeToFree, err = cmutil.ParseSizeInBytesE(sizeToFreeStr)
			if err != nil {
				return errors.Wrapf(err, "invalid --size-to-free value: %s", sizeToFreeStr)
			}
		}

		// 查找所有配置文件
		cnfFiles, err := util.FindBackupConfigFiles("")
		if err != nil {
			return errors.Wrap(err, "find backup config files")
		}
		if len(cnfFiles) == 0 {
			return errors.New("no dbbackup.*.ini config files found")
		}

		// 解析配置文件，过滤端口
		var configs []*config.BackupConfig
		portsMap := make(map[int]bool)
		for _, p := range ports {
			portsMap[p] = true
		}

		for _, cnfFile := range cnfFiles {
			cnf := &config.BackupConfig{}
			viper.Reset()
			if err := initConfig(cnfFile, cnf, logger.Log); err != nil {
				logger.Log.Warnf("failed to parse config %s: %v, skip", cnfFile, err)
				continue
			}
			// 过滤端口
			if len(portsMap) > 0 && !portsMap[cnf.Public.MysqlPort] {
				continue
			}
			configs = append(configs, cnf)
		}
		if len(configs) == 0 {
			logger.Log.Info("no matching config files for the specified ports")
			return nil
		}

		// 获取 backupDir（所有端口应该共享同一个 backupDir）
		backupDir := configs[0].Public.BackupDir
		logger.Log.Infof("remove_backups: backupDir=%s, ports=%v, sizeToFree=%d, maxDiskUsedPct=%.1f%%",
			backupDir, ports, sizeToFree, maxDiskUsedPct)

		// 计算需要释放的空间
		needToFree, err := calcNeedToFree(backupDir, sizeToFree, maxDiskUsedPct)
		if err != nil {
			return err
		}
		if needToFree <= 0 {
			logger.Log.Info("disk space already meets the requirement, no need to remove backups")
			return nil
		}
		logger.Log.Infof("need to free %d bytes (%.2f GB)", needToFree, float64(needToFree)/1024/1024/1024)

		// 按天从旧到新逐步清理
		// 策略：找到所有端口中最大的 OldFileLeftDay，从最大天数开始清理
		// 每轮清理所有端口的 N 天前的备份，然后检查是否满足需求
		var totalFreed int64
		maxDays := getMaxExpireDays(configs)

		// 从最旧的开始清理（expireDays 从大到小）
		// expireDays=N 表示清理 N 天前的备份
		// 我们从 maxDays 开始，逐步减小到 0
		expireDaysList := make([]int, 0, maxDays+1)
		for d := maxDays; d >= 0; d-- {
			expireDaysList = append(expireDaysList, d)
		}

		for _, expireDays := range expireDaysList {
			if totalFreed >= needToFree {
				break
			}
			logger.Log.Infof("trying to remove backups older than %d days for all ports", expireDays)
			for _, cnf := range configs {
				if totalFreed >= needToFree {
					break
				}
				freed, err := backupexe.DeleteOldBackup(&cnf.Public, expireDays)
				if err != nil {
					logger.Log.Warnf("delete old backup for port %d expireDays=%d err: %v",
						cnf.Public.MysqlPort, expireDays, err)
				}
				if freed > 0 {
					totalFreed += freed
					logger.Log.Infof("freed %d bytes (%.2f GB) for port %d with expireDays=%d, total freed: %d bytes (%.2f GB)",
						freed, float64(freed)/1024/1024/1024,
						cnf.Public.MysqlPort, expireDays,
						totalFreed, float64(totalFreed)/1024/1024/1024)
				}
			}
		}

		if totalFreed >= needToFree {
			logger.Log.Infof("successfully freed %d bytes (%.2f GB), meets the requirement",
				totalFreed, float64(totalFreed)/1024/1024/1024)
		} else {
			logger.Log.Warnf("freed %d bytes (%.2f GB), but still not enough (need %d bytes = %.2f GB)",
				totalFreed, float64(totalFreed)/1024/1024/1024,
				needToFree, float64(needToFree)/1024/1024/1024)
		}
		fmt.Printf("total freed: %d bytes (%.2f GB)\n", totalFreed, float64(totalFreed)/1024/1024/1024)
		return nil
	},
}

// calcNeedToFree 计算需要释放的空间大小
// 取 sizeToFree 和 maxDiskUsedPct 两个条件中需要释放更多空间的那个
func calcNeedToFree(backupDir string, sizeToFree int64, maxDiskUsedPct float64) (int64, error) {
	var needToFree int64

	if sizeToFree > 0 {
		needToFree = sizeToFree
	}

	if maxDiskUsedPct > 0 {
		diskInfo, err := util.DiskUsage(backupDir)
		if err != nil {
			return 0, errors.Wrap(err, "get disk usage")
		}
		// 当前使用率
		currentUsedPct := float64(diskInfo.Used) / float64(diskInfo.TotalAvail) * 100
		logger.Log.Infof("disk usage: total=%d, used=%d, avail=%d, usedPct=%.1f%%",
			diskInfo.TotalAvail, diskInfo.Used, diskInfo.Avail, currentUsedPct)

		if currentUsedPct > maxDiskUsedPct {
			// 需要释放的空间 = 当前已用 - 目标已用
			targetUsed := uint64(maxDiskUsedPct / 100 * float64(diskInfo.TotalAvail))
			needByPct := int64(diskInfo.Used) - int64(targetUsed)
			if needByPct > needToFree {
				needToFree = needByPct
			}
		}
	}

	return needToFree, nil
}

// getMaxExpireDays 获取所有配置中最大的 OldFileLeftDay，作为清理的起始天数
// 如果都是 0，则默认从 30 天开始
func getMaxExpireDays(configs []*config.BackupConfig) int {
	days := make([]int, 0, len(configs))
	for _, cnf := range configs {
		days = append(days, cnf.Public.OldFileLeftDay)
	}
	sort.Sort(sort.Reverse(sort.IntSlice(days)))
	if len(days) > 0 && days[0] > 0 {
		return days[0]
	}
	return 30 // 默认最多清理 30 天前的备份
}
