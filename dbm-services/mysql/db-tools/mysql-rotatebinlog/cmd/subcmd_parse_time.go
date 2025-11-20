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
	"encoding/json"
	"fmt"
	"time"

	"github.com/spf13/cobra"

	binlog_parser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
)

var parseTimeCmd = &cobra.Command{
	Use:   "parse-time",
	Short: "parse start or stop time for binlog",
	Long:  `parse start or stop time for binlog`,
	RunE: func(cmd *cobra.Command, args []string) error {
		bp, _ := binlog_parser.NewBinlogParse("mysql", 0, time.RFC3339)
		filename := cmd.Flag("filename").Value.String()
		events, err := bp.GetTime(filename, true, true)
		if err != nil {
			return err
		}
		b, _ := json.Marshal(events)
		fmt.Printf("%s: %s\n", filename, b)
		return nil
	},
}

func init() {
	//命令行的flag
	parseTimeCmd.Flags().StringP("filename", "f", "", "binlog file name")
	_ = parseTimeCmd.MarkFlagRequired("filename")
	rootCmd.AddCommand(parseTimeCmd)
}
