/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package handler

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/bkrepo"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/app/sqlserver"
	"dbm-services/mysql/db-simulation/app/sqlserver/precheck"
)

// SqlServerSyntaxHandler SQLServer 语法检查 handler。
// 当前仅提供文件编码前置检查（UTF-8 with BOM），后续会在同一 handler 下扩展 T-SQL 语法检查等能力。
type SqlServerSyntaxHandler struct {
	BaseHandler
}

// RegisterRouter 注册 /sqlserver/syntax/* 路由
func (s *SqlServerSyntaxHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("/sqlserver/syntax")
	{
		r.POST("/check/file", s.CheckFile)
	}
}

// SqlServerCheckFileParam 文件检查请求参数
// 与 MySQL 模块保持字段习惯一致：path 为 bkrepo 基础路径，files 为文件名列表。
type SqlServerCheckFileParam struct {
	BkBizID int      `json:"bk_biz_id"`
	Path    string   `json:"path" binding:"required"`
	Files   []string `json:"files" binding:"gt=0,dive,required"`
}

// SqlServerCheckFileResponse 检查响应体
type SqlServerCheckFileResponse struct {
	// AllPass 是否所有文件都通过检查
	AllPass bool `json:"all_pass"`
	// Results 每个文件的检查结果
	Results []sqlserver.FileCheckResult `json:"results"`
}

var (
	sqlserverDownloadFiles = downloadFilesFromBkRepo
	sqlserverRunPrecheck   = precheck.RunAll
)

// CheckFile 检查一组 SQL 文件的编码是否符合平台要求
// 流程：解析参数 -> 创建临时目录 -> 从 bkrepo 下载 -> 逐文件前置检查 -> 清理临时目录 -> 返回结果
func (s *SqlServerSyntaxHandler) CheckFile(c *gin.Context) {
	var param SqlServerCheckFileParam
	if err := s.Prepare(c, &param); err != nil {
		logger.Error("SqlServer CheckFile prepare failed: %s", err.Error())
		return
	}

	// 建立本次请求的临时工作目录
	tmpDir, err := os.MkdirTemp(workdir, "sqlserver_precheck_"+time.Now().Format("20060102150405")+"_")
	if err != nil {
		logger.Error("create tmp dir failed: %s", err.Error())
		s.SendResponse(c, err, nil)
		return
	}
	defer func() {
		if rmErr := os.RemoveAll(tmpDir); rmErr != nil {
			logger.Warn("remove tmp dir %s failed: %s", tmpDir, rmErr.Error())
		}
	}()

	// 从 bkrepo 并发下载文件（限并发 5，去重）
	fileNames := lo.Uniq(param.Files)
	if err := sqlserverDownloadFiles(param.Path, fileNames, tmpDir); err != nil {
		logger.Error("download files from bkrepo failed: %s", err.Error())
		s.SendResponse(c, err, nil)
		return
	}

	// 逐文件运行前置检查器（具体检查项由 precheck 包内 init() 自注册，此处无需感知）
	results := make([]sqlserver.FileCheckResult, 0, len(fileNames))
	allPass := true
	for _, fileName := range fileNames {
		localPath := filepath.Join(tmpDir, fileName)
		res, checkErr := sqlserverRunPrecheck(localPath)
		if checkErr != nil {
			// 检查器自身异常（如读文件失败），记为 fail 并继续处理其余文件
			logger.Error("precheck %s failed: %s", fileName, checkErr.Error())
			res = sqlserver.FileCheckResult{
				FileName: fileName,
				Status:   sqlserver.FileCheckFail,
				Encoding: "unknown",
				Message:  fmt.Sprintf("precheck internal error: %s", checkErr.Error()),
			}
		}
		// RunAll 短路时 result 可能没有 FileName，此处补齐
		if res.FileName == "" {
			res.FileName = fileName
		}
		if res.Status != sqlserver.FileCheckPass {
			allPass = false
		}
		results = append(results, res)
	}

	c.JSON(http.StatusOK, Response{
		Code:      0,
		Message:   "",
		RequestID: requestID(c),
		Data: SqlServerCheckFileResponse{
			AllPass: allPass,
			Results: results,
		},
	})
}

// bkrepo 客户端单例（handler 层专用；不复用 syntax 包私有的 getBkrepoClient，保持包边界干净）
var (
	sqlserverBkRepoOnce   sync.Once
	sqlserverBkRepoClient *bkrepo.BkRepoClient
)

// getSqlServerBkRepoClient 懒加载获取 bkrepo 客户端
func getSqlServerBkRepoClient() *bkrepo.BkRepoClient {
	sqlserverBkRepoOnce.Do(func() {
		sqlserverBkRepoClient = &bkrepo.BkRepoClient{
			Client:          &http.Client{Transport: &http.Transport{}},
			BkRepoProject:   config.GAppConfig.BkRepo.Project,
			BkRepoPubBucket: config.GAppConfig.BkRepo.PublicBucket,
			BkRepoUser:      config.GAppConfig.BkRepo.User,
			BkRepoPwd:       config.GAppConfig.BkRepo.Pwd,
			BkRepoEndpoint:  config.GAppConfig.BkRepo.EndPointUrl,
		}
	})
	return sqlserverBkRepoClient
}

// downloadFilesFromBkRepo 并发从 bkrepo 下载文件到 tmpDir（并发上限 5）
func downloadFilesFromBkRepo(basePath string, fileNames []string, tmpDir string) error {
	client := getSqlServerBkRepoClient()
	wg := &sync.WaitGroup{}
	sem := make(chan struct{}, 5)
	errCh := make(chan error, len(fileNames))

	for _, fn := range fileNames {
		wg.Add(1)
		go func(fileName string) {
			sem <- struct{}{}
			defer func() { <-sem; wg.Done() }()
			if err := client.Download(basePath, fileName, tmpDir); err != nil {
				errCh <- fmt.Errorf("download %s failed: %w", fileName, err)
			}
		}(fn)
	}
	wg.Wait()
	close(errCh)

	// 汇总首个错误即返回（保持与 MySQL 模块相似的失败处理粒度）
	for err := range errCh {
		if err != nil {
			return err
		}
	}
	return nil
}
