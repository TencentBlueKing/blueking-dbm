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
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/filecontext"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
)

var cleanSpaceCmd = &cobra.Command{
	Use:          "clean-space",
	Short:        "clean-space for binlog disk partition ",
	Long:         `clean-space will run rotate, that may flush logs`,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		// 一次只能运行一个 clean-space
		lockFile, err := filecontext.NewIncrFile("/tmp/mysql-rotatebinlog.lock", 1, 2*time.Second)
		if err != nil {
			return err
		}
		if err := lockFile.Incr(1); err != nil {
			return err
		}
		defer lockFile.Incr(-1)

		configFile := viper.GetString("config")
		comp := rotate.RotateBinlogComp{Config: configFile}
		if err = log.InitLogger(); err != nil {
			return err
		}
		if comp.ConfigObj, err = rotate.InitConfig(configFile); err != nil {
			return err
		}
		vMaxDiskUsedPct := 0.0
		vMaxBinlogTotalSize := "0"
		vSizeToFree := "0"
		if vMaxDiskUsedPct, err = cmd.Flags().GetFloat64("max-disk-used-pct"); err != nil {
			return err
		} else { // 转成成 100 制
			if vMaxDiskUsedPct < 1.0 && vMaxDiskUsedPct > 0.001 {
				viper.Set("public.max_disk_used_pct", int(vMaxDiskUsedPct*100))
			}
		}
		if vMaxBinlogTotalSize, err = cmd.Flags().GetString("max-binlog-total-size"); err != nil {
			return err
		}
		if vSizeToFree, err = cmd.Flags().GetString("size-to-free"); err != nil {
			return err
		}
		if vMaxDiskUsedPct < 0.001 && vMaxBinlogTotalSize == "0" && vSizeToFree == "0" {
			return errors.New("please give one of max-disk-used-pct,max-binlog-total-size,size-to-free")
		}
		return comp.Start()
	},
}

func init() {
	//命令行的flag
	cleanSpaceCmd.Flags().Float64("max-disk-used-pct", 0.0,
		"binlog disk partition space used percent allowed, rewrite public.max_disk_used_pct. format like 10, 0.1")
	cleanSpaceCmd.Flags().String("max-binlog-total-size", "0",
		"max binlog total size allowed for every port, rewrite public.max_binlog_total_size, format like 200g, 2048m")
	cleanSpaceCmd.Flags().String("size-to-free", "0",
		"expect disk size to be freed for every port. format like 200g, 2048m")
	//cleanSpaceCmd.Flags().Bool("force", false, "force clean.")
	//cleanSpaceCmd.Flags().String("public.keep_policy", "most", "most| least")
	//cleanSpaceCmd.Flags().Int("port", 0, "Port filter")

	_ = viper.BindPFlag("public.max_disk_used_pct", cleanSpaceCmd.Flags().Lookup("max-disk-used-pct"))
	_ = viper.BindPFlag("public.max_binlog_total_size", cleanSpaceCmd.Flags().Lookup("max-binlog-total-size"))
	_ = viper.BindPFlag("request-size-to-free", cleanSpaceCmd.Flags().Lookup("size-to-free"))

	rootCmd.AddCommand(cleanSpaceCmd)
}
