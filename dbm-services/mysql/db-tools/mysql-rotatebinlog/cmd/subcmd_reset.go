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
	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
)

var resetCmd = &cobra.Command{
	Use:   "reset",
	Short: "reset binlog sequence from local db",
	Long:  `reset binlog sequence from local db`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO not create db
		if err := models.InitDB(); err != nil {
			return err
		}
		defer models.DB.Conn.Close()
		var whereMap = make(map[string]interface{})
		if port, _ := cmd.Flags().GetIntSlice("port"); len(port) > 0 {
			whereMap["port"] = port
		}
		if clusterId, _ := cmd.Flags().GetIntSlice("cluster-id"); len(clusterId) > 0 {
			whereMap["cluster_id"] = clusterId
		}
		if len(whereMap) == 0 {
			return errors.Errorf("must require --port  or --cluster-id")
		}
		binlogInst := models.BinlogFileModel{}
		_, err := binlogInst.Delete(models.DB.Conn.DB, whereMap)
		return err
	},
}

func init() {
	//命令行的flag
	resetCmd.Flags().IntSlice("cluster-id", []int{}, "ClusterId filter")
	resetCmd.Flags().IntSlice("port", []int{}, "Port filter")

	rootCmd.AddCommand(resetCmd)
}
