// Package bkrepo TODO
package bkrepo

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strconv"
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
	Code      int             `json:"code"`
	Message   string          `json:"message"`
	Data      json.RawMessage `json:"data"`
	RequestId string          `json:"request_id"`
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
	uri, err := url.JoinPath(b.BkRepoEndpoint, "repository/api/node/detail/", b.BkRepoProject, b.BkRepoPubBucket, filepath,
		filename)
	if err != nil {
		logger.Error("url join path failed %s", err.Error())
		return
	}
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

// UploadRespData TODO
type UploadRespData struct {
	Sha256           string `json:"sha256"`
	Md5              string `json:"md5"`
	Size             int64  `json:"size"`
	FullPath         string `json:"fullPath"`
	CreateBy         string `json:"createBy"`
	CreateDate       string `json:"createdDate"`
	LastModifiedBy   string `json:"lastModifiedBy"`
	LastModifiedDate string `json:"lastModifiedDate"`
	Folder           bool   `json:"folder"` // 是否为文件夹
	Path             string `json:"path"`
	Name             string `json:"name"`
	ProjectId        string `json:"projectId"`
	RepoName         string `json:"repoName"`
}

// FileServerInfo 文件服务器
type FileServerInfo struct {
	URL      string `json:"url"`      // 制品库地址
	Bucket   string `json:"bucket"`   // 目标bucket
	Password string `json:"password"` // 制品库 password
	Username string `json:"username"` // 制品库 username
	Project  string `json:"project"`  // 制品库 project
}

func newfileUploadRequest(uri string, params map[string]string, paramName, path string) (*http.Request, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile(paramName, filepath.Base(path))
	if err != nil {
		return nil, err
	}
	_, err = io.Copy(part, file)
	if err != nil {
		return nil, err
	}
	for key, val := range params {
		_ = writer.WriteField(key, val)
	}
	err = writer.Close()
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest(http.MethodPut, uri, body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	return req, err
}

// UploadDirectToBkRepo TODO
func UploadDirectToBkRepo(filepath string, targetURL string, username string, password string) (*BkRepoRespone, error) {
	logger.Info("start upload files from  %s to %s", filepath, targetURL)
	bodyBuf := bytes.NewBufferString("")
	bodyWriter := multipart.NewWriter(bodyBuf)
	fh, err := os.Open(filepath)
	if err != nil {
		logger.Info("error opening file")
		return nil, err
	}
	boundary := bodyWriter.Boundary()
	closeBuf := bytes.NewBufferString("")

	requestReader := io.MultiReader(bodyBuf, fh, closeBuf)
	fi, err := fh.Stat()
	if err != nil {
		fmt.Printf("Error Stating file: %s", filepath)
		return nil, err
	}
	req, err := http.NewRequest("PUT", targetURL, requestReader)
	if err != nil {
		return nil, err
	}
	req.SetBasicAuth(username, password)
	// Set headers for multipart, and Content Length
	req.Header.Set("Content-Type", "multipart/form-data; boundary="+boundary)
	// 文件是否可以被覆盖，默认false
	req.Header.Set("X-BKREPO-OVERWRITE", "True")
	// 文件默认保留半年
	req.Header.Set("X-BKREPO-EXPIRES", "183")
	req.ContentLength = fi.Size() + int64(bodyBuf.Len()) + int64(closeBuf.Len())
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("返回码非200 %d", resp.StatusCode)
	}
	var baseResp BkRepoRespone
	if err = json.NewDecoder(resp.Body).Decode(&baseResp); err != nil {
		return nil, err
	}
	return &baseResp, err
}

// UploadFile 上传文件到蓝盾制品库
// filepath:  本地需要上传文件的路径
// targetURL: 仓库文件完整路径
func UploadFile(filepath, targetURL, username, password string, BkCloudId int, DBCloudToken string) (*BkRepoRespone,
	error) {
	logger.Info("start upload files from  %s to %s", filepath, targetURL)
	if BkCloudId == 0 {
		return UploadDirectToBkRepo(filepath, targetURL, username, password)
	}
	req, err := newfileUploadRequest(
		targetURL, map[string]string{
			"bk_cloud_id":    strconv.Itoa(BkCloudId),
			"db_cloud_token": DBCloudToken,
		}, "file", filepath,
	)
	if err != nil {
		logger.Error("new request failed %s", err.Error())
		return nil, err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body := &bytes.Buffer{}
	_, err = body.ReadFrom(resp.Body)
	if err != nil {
		logger.Error("read from body failed %s", err.Error())
		return nil, err
	}
	logger.Info("respone body:%s", body.String())
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("返回码非200 %d,Message:%s", resp.StatusCode, body.String())
	}
	var baseResp BkRepoRespone
	if err = json.NewDecoder(body).Decode(&baseResp); err != nil {
		return nil, err
	}
	return &baseResp, err
}
