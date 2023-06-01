package cc

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strconv"
	"sync"

	"dbm-services/common/go-pubpkg/cc.v3/utils"

	"github.com/golang/glog"
)

// HostWatcher 主机信息watch
type HostWatcher struct {
	client *Client
	// 查询CC主机对应的项
	fields   []string
	lock     sync.Mutex
	stopped  bool
	outgoing chan Event
	emit     func(Event)
}

func newHostWatcher(client *Client) *HostWatcher {
	w := &HostWatcher{
		client:   client,
		fields:   utils.GetStructTagName(reflect.TypeOf(&Host{})),
		outgoing: make(chan Event),
	}
	w.emit = func(e Event) { w.outgoing <- e }
	return w
}

// HostWatchList TODO
func HostWatchList(client *Client) (Interface, error) {
	w := newHostWatcher(client)
	go w.sync()
	return w, nil
}

func (w *HostWatcher) sync() {
	var cursor string
	for {
		result, err := resourceWatch(w.client, HostResource, cursor, w.fields)
		if err != nil {
			w.emit(Event{
				Type:   Error,
				Object: fmt.Sprintf("HostWatcher failed, cursor:%s - err: %v", cursor, err),
			})
			// 出现异常，重置cursor
			cursor = ""
			continue
		}
		glog.Infof("HostWatcher - Cursor: %s, RequestId: %s, EventCount: %d", cursor, result.RequestId, len(result.BKEvents))
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
			var host Host
			if err := json.Unmarshal(item.BKDetail, &host); err != nil {
				w.emit(Event{
					Type:   Error,
					Object: fmt.Sprintf("TypeErr host: Detail: %v - Err: %s", string(item.BKDetail), err),
				})
				continue
			}
			w.emit(Event{
				Key:    strconv.Itoa(host.BKHostId),
				Object: &host,
				Type:   EventType(item.BKEventType),
				Cursor: item.BKCursor,
			})
		}
	}
}

// ResultChan TODO
// Return event chan
func (w *HostWatcher) ResultChan() <-chan Event {
	return w.outgoing
}

// Stop watcher
func (w *HostWatcher) Stop() {
	w.lock.Lock()
	defer w.lock.Unlock()
	// Prevent double channel closes.
	if !w.stopped {
		w.stopped = true
		close(w.outgoing)
	}
}
