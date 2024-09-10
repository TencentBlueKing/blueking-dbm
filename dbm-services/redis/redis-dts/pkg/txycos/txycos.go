// Package txycos TODO
package txycos

import (
	"context"
	"fmt"
	"net/http"
	"net/url"

	"dbm-services/redis/redis-dts/util"

	"github.com/spf13/viper"
	"github.com/tencentyun/cos-go-sdk-v5"
	"go.uber.org/zap"
)

// TxyCosWoker 腾讯云cos客户端
type TxyCosWoker struct {
	URL       string `json:"url"`       // 接口地址
	SecretID  string `json:"secretId"`  // 密钥
	SecretKey string `json:"secretKey"` // 密钥的密文
	cosClient *cos.Client
	logger    *zap.Logger
}

// NewTxyCosWoker 创建一个TxyCosWoker
func NewTxyCosWoker(logger *zap.Logger) (ret *TxyCosWoker, err error) {
	ret = &TxyCosWoker{
		URL:       viper.GetString("txycos.url"),
		SecretID:  viper.GetString("txycos.secret_id"),
		SecretKey: viper.GetString("txycos.secret_key"),
		logger:    logger,
	}
	if ret.URL == "" || ret.SecretID == "" || ret.SecretKey == "" {
		err = fmt.Errorf("txycos.url:%s,secret_id:%s,secret_key:%s cannot be empty", ret.URL, ret.SecretID, ret.SecretKey)
		ret.logger.Error(err.Error())
		return nil, err
	}
	u, err := url.Parse(ret.URL)
	if err != nil {
		err = fmt.Errorf("txycos.url parse failed,err:%v,url:%s", err, ret.URL)
		ret.logger.Error(err.Error())
		return nil, err
	}
	b := &cos.BaseURL{BucketURL: u}
	ret.cosClient = cos.NewClient(b, &http.Client{
		Transport: &cos.AuthorizationTransport{
			SecretID:  ret.SecretID,
			SecretKey: ret.SecretKey,
		},
	})
	return
}

// BucketList 桶列表
func (t *TxyCosWoker) BucketList() (ret *cos.ServiceGetResult, err error) {
	ret, resp, err := t.cosClient.Service.Get(context.Background())
	if err != nil {
		err = fmt.Errorf("BucketList failed,err:%v", err)
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("BucketList failed,resp.StatusCode:%d\n", resp.StatusCode)
		t.logger.Error(err.Error())
		return
	}
	return
}

// BucketCreate 创建存储桶
func (t *TxyCosWoker) BucketCreate() (err error) {
	opt := &cos.BucketPutOptions{
		XCosACL: "private",
	}
	resp, err := t.cosClient.Bucket.Put(context.Background(), opt)
	if err != nil {
		err = fmt.Errorf("BucketCreate failed,err:%v", err)
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("BucketCreate failed,resp.StatusCode:%d\n", resp.StatusCode)
		t.logger.Error(err.Error())
		return
	}
	return nil
}

// PutAFile 文件上传
func (t *TxyCosWoker) PutAFile(key, filepath string) (err error) {
	opt := &cos.ObjectPutOptions{
		ObjectPutHeaderOptions: &cos.ObjectPutHeaderOptions{
			ContentType: "text/html",
		},
		ACLHeaderOptions: &cos.ACLHeaderOptions{
			XCosACL: "private",
		},
	}

	resp, err := t.cosClient.Object.PutFromFile(context.Background(), key, filepath, opt)
	if err != nil {
		err = fmt.Errorf("PutAFile failed,err:%v\n", err)
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("PutAFile failed,resp.StatusCode:%d,key:%s,filepath:%s\n", resp.StatusCode, key, filepath)
		t.logger.Error(err.Error())
		return
	}
	return nil
}

// GetFileList 获取文件列表
func (t *TxyCosWoker) GetFileList(prefix string, maxKeys int) (ret *cos.BucketGetResult, err error) {

	opt := &cos.BucketGetOptions{
		Prefix:  prefix,
		MaxKeys: maxKeys,
	}

	ret, resp, err := t.cosClient.Bucket.Get(context.Background(), opt)
	if err != nil {
		err = fmt.Errorf("GetFileList failed,err:%v,opt:%s\n", err, util.ToString(opt))
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("GetFileList failed,resp.StatusCode:%d,opt:%s\n", resp.StatusCode, util.ToString(opt))
		t.logger.Error(err.Error())
		return
	}
	return
}

// DownloadAFile 从存储桶下载文件
func (t *TxyCosWoker) DownloadAFile(key, savePath string) (err error) {
	opt := &cos.MultiDownloadOptions{
		ThreadPoolSize: 5,
	}
	resp, err := t.cosClient.Object.Download(
		context.Background(), key, savePath, opt,
	)
	if err != nil {
		err = fmt.Errorf("DownloadAFile failed,err:%v\n", err)
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("DownloadAFile failed,resp.StatusCode:%d,key:%s\n", resp.StatusCode, key)
		t.logger.Error(err.Error())
		return
	}
	return nil
}

// DeleteAFile 从存储桶删除文件
func (t *TxyCosWoker) DeleteAFile(key string) (err error) {
	resp, err := t.cosClient.Object.Delete(context.Background(), key)
	if err != nil {
		err = fmt.Errorf("DeleteAFile failed,err:%v,key:%s\n", err, key)
		t.logger.Error(err.Error())
		return
	}
	if resp.StatusCode != http.StatusOK {
		err = fmt.Errorf("DeleteAFile failed,resp.StatusCode:%d,key:%s\n", resp.StatusCode, key)
		t.logger.Error(err.Error())
		return
	}
	return nil
}
