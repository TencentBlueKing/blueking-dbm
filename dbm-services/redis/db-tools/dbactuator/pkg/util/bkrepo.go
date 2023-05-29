package util

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

// FileServerInfo 文件服务器
type FileServerInfo struct {
	URL      string `json:"url"`      // 制品库地址
	Bucket   string `json:"bucket"`   // 目标bucket
	Password string `json:"password"` // 制品库 password
	Username string `json:"username"` // 制品库username
	Project  string `json:"project"`  // 制品库project
}

// UploadFile 上传文件到蓝盾制品库
// filepath: 本地需要上传文件的路径
// targetURL: 仓库文件完整路径
func UploadFile(filepath string, targetURL string, username string, password string) (*http.Response, error) {

	userMsg := fmt.Sprintf(username + ":" + password)
	token := base64.StdEncoding.EncodeToString([]byte(userMsg))
	msg := fmt.Sprintf("start upload files from  %s to %s", filepath, targetURL)
	mylog.Logger.Info(msg)
	bodyBuf := bytes.NewBufferString("")
	bodyWriter := multipart.NewWriter(bodyBuf)

	fh, err := os.Open(filepath)
	if err != nil {
		mylog.Logger.Info("error opening file")
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

	// Set headers for multipart, and Content Length
	req.Header.Set("Content-Type", "multipart/form-data; boundary="+boundary)
	// 文件是否可以被覆盖，默认false
	req.Header.Set("X-BKREPO-OVERWRITE", "True")
	// 文件默认保留半年
	req.Header.Set("X-BKREPO-EXPIRES", "183")
	req.Header.Set("Authorization", "Basic "+token)
	req.ContentLength = fi.Size() + int64(bodyBuf.Len()) + int64(closeBuf.Len())
	return http.DefaultClient.Do(req)
	// return response, err
}

// DownloadFile  从蓝盾制品库下载文件
// filepath: 本地保存文件压缩包名
// targetURL: 仓库文件完整路径
func DownloadFile(filepath string, targetURL string, username string, password string) (err error) {
	msg := fmt.Sprintf("start download files from %s to %s", targetURL, filepath)
	mylog.Logger.Info(msg)
	userMsg := fmt.Sprintf(username + ":" + password)
	token := base64.StdEncoding.EncodeToString([]byte(userMsg))
	outFile, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer outFile.Close()

	resp, err := http.Get(targetURL)
	if err != nil {
		return err
	}
	resp.Header.Set("Authorization", "Basic "+token)
	defer resp.Body.Close()

	// Check server response
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	// Writer the body to file
	_, err = io.Copy(outFile, resp.Body)
	if err != nil {
		return err
	}
	mylog.Logger.Info("finish download files")

	return nil

}
