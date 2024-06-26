package service

import (
	"bytes"
	"dbm-services/mysql/db-partition/model"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path"
)

// UploadDirectToBkRepo 上传文件到介质中心
func UploadDirectToBkRepo(filename string) (*BkRepoRespone, error) {
	// 路径需要包含文件名称
	targetURL, err := url.JoinPath(model.BkRepo.EndPointUrl,
		path.Join("generic", model.BkRepo.Project, model.BkRepo.PublicBucket, "mysql", "partition", filename))
	if err != nil {
		slog.Error("get url fail")
		return nil, err
	}
	slog.Info(fmt.Sprintf("start upload files from  %s to %s", filename, targetURL))
	bodyBuf := bytes.NewBufferString("")
	bodyWriter := multipart.NewWriter(bodyBuf)
	fh, err := os.Open(filename)
	if err != nil {
		slog.Error("opening file error", "err", err)
		return nil, err
	}
	boundary := bodyWriter.Boundary()
	closeBuf := bytes.NewBufferString("")

	requestReader := io.MultiReader(bodyBuf, fh, closeBuf)
	fi, err := fh.Stat()
	if err != nil {
		slog.Error("stating file error", "file", filename, "err", err)
		return nil, err
	}
	req, err := http.NewRequest("PUT", targetURL, requestReader)
	if err != nil {
		return nil, err
	}
	req.SetBasicAuth(model.BkRepo.User, model.BkRepo.Pwd)
	// Set headers for multipart, and Content Length
	req.Header.Set("Content-Type", "multipart/form-data; boundary="+boundary)
	// 文件是否可以被覆盖，默认false
	req.Header.Set("X-BKREPO-OVERWRITE", "True")
	// 文件默认保留半年
	req.Header.Set("X-BKREPO-EXPIRES", "15")
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

// BkRepoRespone 响应
type BkRepoRespone struct {
	Code      int             `json:"code"`
	Message   string          `json:"message"`
	Data      json.RawMessage `json:"data"`
	RequestId string          `json:"request_id"`
}
