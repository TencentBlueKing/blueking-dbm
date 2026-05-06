/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package osutil

import (
	"encoding/json"
	"fmt"
	"net/url"
	"path"
	"reflect"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/logger"
)

type UploadBkRepoParam struct {
	BackupFileName string     `json:"backup_file_name"`
	BackupDir      string     `json:"backup_dir"`
	BkCloudId      int        `json:"bk_cloud_id"`    // 所在的云区域
	DBCloudToken   string     `json:"db_cloud_token"` // 云区域token
	FileServer     FileServer `json:"fileserver"`
}

// FileServer TODO
type FileServer struct {
	URL        string `json:"url"`         // 制品库地址
	Bucket     string `json:"bucket"`      // 目标bucket
	Password   string `json:"password"`    // 制品库 password
	Username   string `json:"username"`    // 制品库 username
	Project    string `json:"project"`     // 制品库 project
	UploadPath string `json:"upload_path"` // 上传路径
}

// Upload do upload comp
func (c UploadBkRepoParam) Upload() (err error) {
	if reflect.DeepEqual(c.FileServer, FileServer{}) {
		logger.Info("the fileserver parameter is empty no upload is required ~")
		return nil
	}
	schemafile := path.Join(c.BackupDir, c.BackupFileName)
	r := path.Join("generic", c.FileServer.Project, c.FileServer.Bucket, c.FileServer.UploadPath)
	uploadUrl, err := url.JoinPath(c.FileServer.URL, r, "/")
	if err != nil {
		logger.Error("call url joinPath failed %s ", err.Error())
		return err
	}
	if c.BkCloudId == 0 {
		uploadUrl, err = url.JoinPath(
			c.FileServer.URL, path.Join(
				"/generic", c.FileServer.Project,
				c.FileServer.Bucket, c.FileServer.UploadPath, c.BackupFileName,
			),
		)
		if err != nil {
			logger.Error("call url joinPath failed %s ", err.Error())
			return err
		}
	}
	logger.Info("bk_cloud_id:%d,upload url:%s", c.BkCloudId, uploadUrl)
	resp, err := bkrepo.UploadFile(
		schemafile, uploadUrl, c.FileServer.Username, c.FileServer.Password,
		c.BkCloudId, c.DBCloudToken,
	)
	if err != nil {
		logger.Error("upload sqlfile error %s", err.Error())
		return err
	}
	if resp.Code != 0 {
		errMsg := fmt.Sprintf(
			"upload response code is %d,response msg:%s,traceId:%s",
			resp.Code,
			resp.Message,
			resp.RequestId,
		)
		logger.Error(errMsg)
		return fmt.Errorf("%s", errMsg)
	}
	logger.Info("resp: code:%d,msg:%s,traceid:%s", resp.Code, resp.Message, resp.RequestId)
	var uploadRespdata bkrepo.UploadRespData
	if err := json.Unmarshal(resp.Data, &uploadRespdata); err != nil {
		logger.Error("unmarshal upload response data failed %s", err.Error())
		return err
	}
	logger.Info("%v", uploadRespdata)
	return nil
}
