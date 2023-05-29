package cc

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/golang/glog"
)

// Interface 资源Watch接口
type Interface interface {
	// Stop s watching. Will close the channel returned by ResultChan()
	Stop()

	// ResultChan TODO
	// Returns a chan which will receive all the events.
	ResultChan() <-chan Event
}

// EventType TODO
// watch类型
type EventType string

const (
	// Added TODO
	Added EventType = "create"
	// Modified TODO
	Modified EventType = "update"
	// Deleted TODO
	Deleted EventType = "delete"
	// Error TODO
	Error EventType = "error"
)

// Event TODO
// watch事件信息
type Event struct {
	// 事件唯一标识
	Key string
	// 事件具体对象
	Object interface{}
	// 资源类型
	Kind string
	// 事件类型
	Type EventType
	// CC的游标
	Cursor string
}

const (
	// WatcherURL TODO
	WatcherURL = "/api/c/compapi/v2/cc/resource_watch"
)

// resourceWatch 执行资源的watch
// resourceWatchType: watch的资源类型
// cursor:  watch开始位置
// fields: 需要返回的项（值），对于不同的资源，返回不同的结果
func resourceWatch(client *Client, resourceWatchType ResourceWatchType, cursor string,
	fields []string) (*ResourceWatchResponse, error) {
	param := &ResourceWatchParam{
		BKFields:   fields,
		BKResource: resourceWatchType,
	}
	if cursor != "" {
		param.BKCursor = cursor
	} else {
		// 如果当前游标为空：包括第一次启动服务，或者watch异常时
		// 取前1分钟的事件
		param.BKStartFrom = time.Now().Add(time.Second * -60).Unix()
	}
	resp, err := client.Do(http.MethodPost, WatcherURL, param)
	if err != nil {
		return nil, err
	}
	glog.V(5).Infof("Watch response: %+v", resp)
	var result ResourceWatchResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, fmt.Errorf("RequestId: %s, err: %v", resp.RequestId, err)
	}
	result.RequestId = resp.RequestId
	return &result, nil
}
