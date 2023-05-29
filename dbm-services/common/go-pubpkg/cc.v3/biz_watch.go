package cc

import (
	"dbm-services/common/go-pubpkg/cc.v3/utils"
	"encoding/json"
	"fmt"
	"reflect"
	"strconv"
	"sync"

	"github.com/golang/glog"
)

// BizWatcher TODO
type BizWatcher struct {
	client *Client
	// 查询CC业务信息对应的项
	fields   []string
	lock     sync.Mutex
	stopped  bool
	outgoing chan Event
	emit     func(Event)
}

func newBizWatcher(client *Client) *BizWatcher {
	w := &BizWatcher{
		client:   client,
		fields:   utils.GetStructTagName(reflect.TypeOf(&Biz{})),
		outgoing: make(chan Event),
	}
	w.emit = func(e Event) { w.outgoing <- e }
	return w
}

// BizWatchList returns a new BizWatcher server
func BizWatchList(client *Client) (Interface, error) {
	w := newBizWatcher(client)
	go w.sync()
	return w, nil
}

func (w *BizWatcher) sync() {
	var cursor string
	for {
		result, err := resourceWatch(w.client, BizResource, cursor, w.fields)
		if err != nil {
			w.emit(Event{
				Type:   Error,
				Object: fmt.Sprintf("BizWatcher failed: %v", err),
			})
			// 出现异常，重置cursor
			cursor = ""
			continue
		}
		glog.Infof("BizWatcher - Cursor: %s, RequestId: %s, EventCount: %d", cursor, result.RequestId, len(result.BKEvents))
		// 如果BKEvents为空，那么需要重置cursor
		// 要不从当前的cursor watch就会一直报错
		if len(result.BKEvents) == 0 {
			cursor = ""
			continue
		}
		for _, item := range result.BKEvents {
			cursor = item.BKCursor
			if string(item.BKDetail) == "null" {
				continue
			}
			var biz Biz
			if err := json.Unmarshal(item.BKDetail, &biz); err != nil {
				w.emit(Event{
					Type:   Error,
					Object: fmt.Sprintf("TypeErr biz: Detail: %v - Err: %s", string(item.BKDetail), err),
				})
				continue
			}
			w.emit(Event{
				Key:    strconv.Itoa(biz.ApplicationID),
				Object: &biz,
				Type:   EventType(item.BKEventType),
			})
		}
	}
}

// ResultChan TODO
// Return event chan
func (w *BizWatcher) ResultChan() <-chan Event {
	return w.outgoing
}

// Stop watcher
func (w *BizWatcher) Stop() {
	w.lock.Lock()
	defer w.lock.Unlock()
	// Prevent double channel closes.
	if !w.stopped {
		w.stopped = true
		close(w.outgoing)
	}
}
