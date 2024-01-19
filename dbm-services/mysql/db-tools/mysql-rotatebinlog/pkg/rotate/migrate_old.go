/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package rotate

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/mohae/deepcopy"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	binlog_parser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
)

func DumpOldFileList(dir string, portMap map[int]models.BinlogFileModel) error {
	//binlog_backup_file_list := filepath.Join(dir, "binlog_backup_file_list.log")
	binlog_task := filepath.Join(dir, "binlog_task.log")
	flagFile := filepath.Join(dir, "rotatebinlog_new.done")

	if cmutil.FileExists(flagFile) {
		// 已经dump
		fmt.Println("already done", flagFile)
		return nil
	} else if !cmutil.FileExists(dir) {
		// 老rotate_logbin不存在
		fmt.Println("dir not exists", dir)
		return nil
	}

	// 2021-09-24:/data/mysqllog/20000/binlog/binlog20000.000076:taskid:9856951663
	f2, err := os.Open(binlog_task)
	if err != nil {
		return err
	}
	scanner2 := bufio.NewScanner(f2)
	if err = log.InitReporter(); err != nil {
		return err
	}
	for scanner2.Scan() {
		binlogTask := strings.Split(scanner2.Text(), ":")
		binlogFile := binlogTask[1]
		taskId := binlogTask[3]

		ff, err := os.Stat(binlogFile)
		if err != nil {
			// 有可能没权限，有可能不存在
			if os.IsNotExist(err) {
				continue
			} else {
				return errors.WithMessagef(err, "stat binlog file %s", binlogFile)
			}
		}

		var fileObj models.BinlogFileModel
		binlogName := filepath.Base(binlogFile)
		port := getPortFromBinlogName(binlogName)
		if port == 0 {
			return errors.Errorf("fail to get port from %s", binlogName)
		} else {
			if inst, ok := portMap[port]; !ok {
				return errors.Errorf("fail to get instance info for port %d", port)
			} else {
				fileObj = deepcopy.Copy(inst).(models.BinlogFileModel)
			}
		}

		if cast.ToInt64(taskId) != 0 {
			fileObj.BackupTaskid = taskId
			fileObj.BackupStatus = 4
		} else {
			logger.Warn("binlog file %s task_id=%s", binlogFile, taskId)
			fileObj.BackupStatus = 0
		}

		fileObj.Filename = binlogName
		fileObj.Filesize = ff.Size()
		fileObj.FileMtime = ff.ModTime().Format(time.RFC3339)

		bp, _ := binlog_parser.NewBinlogParse("", 0, time.RFC3339)
		events, err := bp.GetTimeIgnoreStopErr(binlogFile, true, true)
		if err != nil {
			logger.Warn("binlog file get time failed", binlogFile)
		} else {
			fileObj.StartTime = events[0].EventTime
			fileObj.StopTime = events[1].EventTime
		}

		if err = fileObj.Save(models.DB.Conn, true); err != nil {
			return errors.WithMessagef(err, "write sqlite %s", binlogFile)
		} else {
			log.Reporter().Result.Println(fileObj)
		}
	}
	if err := scanner2.Err(); err != nil {
		return err
	}
	if err = os.WriteFile(flagFile, []byte("ok"), 0755); err != nil {
		return errors.WithMessagef(err, "fail to write flag file %s:ok", flagFile)
	}
	return nil
}

var ReBinlogName = regexp.MustCompile(`binlog(\d*)\.\d+`)

func getPortFromBinlogName(name string) int {
	matches := ReBinlogName.FindStringSubmatch(name)
	if len(matches) == 2 {
		if matches[1] == "" {
			return 3306
		}
		port := cast.ToInt(matches[1])
		return port
	} else {
		return 0
	}
}
