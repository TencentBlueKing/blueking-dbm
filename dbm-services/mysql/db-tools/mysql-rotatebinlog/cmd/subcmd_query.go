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
	"os"

	sq "github.com/Masterminds/squirrel"
	"github.com/olekukonko/tablewriter"
	"github.com/spf13/cast"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
)

var queryCmd = &cobra.Command{
	Use:   "query",
	Short: "query binlog file status",
	Long:  `query binlog file status from local db`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO not create db
		if err := models.InitDB(); err != nil {
			return err
		}
		defer models.DB.Conn.Close()
		binlogInst := models.BinlogFileModel{}
		//var whereMap = make(map[string]interface{})
		sqlBuilder := sq.Select(
			"bk_biz_id", "cluster_id", "cluster_domain", "db_role", "host", "port", "filename",
			"filesize", "start_time", "stop_time", "file_mtime", "backup_status", "task_id",
		).From(binlogInst.TableName())

		if port, _ := cmd.Flags().GetInt("port"); port != 0 {
			sqlBuilder = sqlBuilder.Where(sq.Eq{"port": port})
		}
		if clusterId, _ := cmd.Flags().GetInt("cluster-id"); clusterId != 0 {
			sqlBuilder = sqlBuilder.Where(sq.Eq{"cluster_id": clusterId})
		}
		if status, _ := cmd.Flags().GetIntSlice("status"); len(status) != 0 {
			sqlBuilder = sqlBuilder.Where(sq.Eq{"backup_status": status})
		}
		if filenameLike, _ := cmd.Flags().GetString("filename-like"); filenameLike != "" {
			sqlBuilder = sqlBuilder.Where(sq.Like{"filename": filenameLike})
		}
		if limitNum, _ := cmd.Flags().GetInt("limit"); limitNum != 0 {
			sqlBuilder = sqlBuilder.Limit(uint64(limitNum))
		}

		sqlBuilder = sqlBuilder.OrderBy("filename desc")
		files, err := binlogInst.QueryWithBuildWhere(models.DB.Conn, &sqlBuilder)
		if err != nil {
			return err
		}
		table := tablewriter.NewWriter(os.Stdout)
		table.SetAutoWrapText(false)
		table.SetAutoFormatHeaders(false)
		table.SetAutoMergeCellsByColumnIndex([]int{0, 1, 2})
		table.SetRowLine(true)
		table.SetHeader([]string{"ClusterDomain", "DBRole", "Port", "Filename", "Filesize", "FimeMtime", "StopTime",
			"BackupStatus", "ClusterId", "BkBizId", "Host"})
		for _, fi := range files {
			if fi != nil {
				table.Append([]string{
					fi.ClusterDomain,
					fi.DBRole,
					cast.ToString(fi.Port),
					fi.Filename,
					cast.ToString(fi.Filesize),
					fi.FileMtime,
					fi.StopTime,
					cast.ToString(fi.BackupStatus),
					cast.ToString(fi.ClusterId),
					cast.ToString(fi.BkBizId),
					fi.Host,
				})

			}
		}
		//table.SetFooter([]string{"Rows", cast.ToString(table.NumLines()), "", "", "", "", ""})
		table.Render()
		return nil
	},
}

func init() {
	//命令行的flag
	queryCmd.Flags().StringP("filename-like", "n", "", "file name like query")
	queryCmd.Flags().IntSlice("status", nil, "task status id, comma separated")
	queryCmd.Flags().Int("cluster-id", 0, "ClusterId filter")
	queryCmd.Flags().Int("port", 0, "Port filter")
	queryCmd.Flags().IntP("limit", "l", 10, "rows limit num")

	queryCmd.Flags().StringP("format", "m", "table", "output format, table | json")
	// bind to viper
	_ = viper.BindPFlag("format", queryCmd.Flags().Lookup("format"))

	rootCmd.AddCommand(queryCmd)
}
