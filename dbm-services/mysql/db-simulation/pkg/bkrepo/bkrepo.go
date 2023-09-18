// Package bkrepo TODO
package bkrepo

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"

	util "dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

/*
	API: GET /generic/{project}/{repo}/{path}?download=true
	API 名称: download
	功能说明：

	中文：下载通用制品文件
	English：download generic file
	请求体 此接口请求体为空
*/

// BkRepoClient TODO
type BkRepoClient struct {
	Client          *http.Client
	BkRepoProject   string
	BkRepoPubBucket string
	BkRepoEndpoint  string
	BkRepoUser      string
	BkRepoPwd       string
}

// BkRepoRespone TODO
type BkRepoRespone struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
	TraceId string          `json:"traceId"`
}

// getBaseUrl TODO
//
//	@receiver b
func (b *BkRepoClient) getBaseUrl() string {
	u, err := url.Parse(b.BkRepoEndpoint)
	if err != nil {
		log.Fatal(err)
	}
	r, err := url.Parse(path.Join(u.Path, "generic", b.BkRepoProject, b.BkRepoPubBucket))
	if err != nil {
		log.Fatal(err)
	}
	uri := u.ResolveReference(r).String()
	logger.Info("uri:%s", uri)
	return uri
}

// Download 从制品库下载文件
//
//	@receiver b
func (b *BkRepoClient) Download(sqlpath, filename, downloaddir string) (err error) {
	uri := b.getBaseUrl() + path.Join("/", sqlpath, filename) + "?download=true"
	logger.Info("The download url is %s", uri)
	req, err := http.NewRequest(http.MethodGet, uri, nil)
	if err != nil {
		return err
	}
	if strings.Contains(filename, "..") {
		return fmt.Errorf("%s there is a risk of path crossing", filename)
	}
	fileAbPath, err := filepath.Abs(path.Join(downloaddir, filename))
	if err != nil {
		return err
	}
	f, err := os.Create(fileAbPath)
	if err != nil {
		return err
	}
	req.SetBasicAuth(b.BkRepoUser, b.BkRepoPwd)
	resp, err := b.Client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	logger.Info("respone code %d", resp.StatusCode)
	if resp.StatusCode != http.StatusOK {
		bs, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}
		return fmt.Errorf("respone code is %d,respone body is :%s", resp.StatusCode, string(bs))
	}
	size, err := io.Copy(f, resp.Body)
	if err != nil {
		return err
	}
	logger.GetLogger().Info(fmt.Sprintf("Downloaded a file %s with size %d", filename, size))
	fileNodeInfo, err := b.QueryFileNodeInfo(sqlpath, filename)
	if err != nil {
		return err
	}
	logger.Info("node detail %v", fileNodeInfo)
	if size != int64(fileNodeInfo.Size) {
		bs, _ := os.ReadFile(fileAbPath)
		return fmt.Errorf("body:%s,current file:%s source file size is inconsistent,current file is:%d,bkrepo file is：%d",
			string(bs), filename, size,
			fileNodeInfo.Size)
	}

	currentFileMd5, err := util.GetFileMd5(fileAbPath)
	if err != nil {
		return err
	}
	if currentFileMd5 != fileNodeInfo.Md5 {
		return fmt.Errorf("current file:%s  source file md5 is inconsistent,current file is:%s,bkrepo file is:%s", filename,
			currentFileMd5,
			fileNodeInfo.Md5)
	}
	return nil
}

// FileNodeInfo TODO
type FileNodeInfo struct {
	Name     string            `json:"name"`
	Sha256   string            `json:"sha256"`
	Md5      string            `json:"md5"`
	Size     int               `json:"size"`
	Metadata map[string]string `json:"metadata"`
}

// QueryFileNodeInfo TODO
// QueryMetaData 查询文件元数据信息
//
//	@receiver b
func (b *BkRepoClient) QueryFileNodeInfo(filepath, filename string) (realData FileNodeInfo, err error) {
	var baseResp BkRepoRespone
	u, err := url.Parse(b.BkRepoEndpoint)
	if err != nil {
		return
	}
	r, err := url.Parse(path.Join("repository/api/node/detail/", b.BkRepoProject, b.BkRepoPubBucket, filepath, filename))
	if err != nil {
		logger.Error(err.Error())
		return
	}
	uri := u.ResolveReference(r).String()
	logger.Info("query node detail url %s", uri)
	req, err := http.NewRequest(http.MethodGet, uri, nil)
	if err != nil {
		return FileNodeInfo{}, err
	}
	resp, err := b.Client.Do(req)
	if err != nil {
		return FileNodeInfo{}, err
	}
	defer resp.Body.Close()
	if err = json.NewDecoder(resp.Body).Decode(&baseResp); err != nil {
		return FileNodeInfo{}, err
	}
	if baseResp.Code != 0 {
		return FileNodeInfo{}, fmt.Errorf("bkrepo Return Code: %d,Messgae:%s", baseResp.Code, baseResp.Message)
	}
	if err = json.Unmarshal([]byte(baseResp.Data), &realData); err != nil {
		return FileNodeInfo{}, err
	}
	return
}
