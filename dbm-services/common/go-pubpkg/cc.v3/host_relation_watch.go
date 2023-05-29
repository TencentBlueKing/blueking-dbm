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

// HostRelationWatcher is a the HostRelationWatcher server
type HostRelationWatcher struct {
	client *Client
	// 查询CC主机与业务模块关系对应的项
	fields   []string
	lock     sync.Mutex
	stopped  bool
	outgoing chan Event
	emit     func(Event)
}

func newHostRelationWatcher(client *Client) *HostRelationWatcher {
	w := &HostRelationWatcher{
		client:   client,
		fields:   utils.GetStructTagName(reflect.TypeOf(&HostBizModule{})),
		outgoing: make(chan Event),
	}
	w.emit = func(e Event) { w.outgoing <- e }
	return w
}

// HostRelationWatchList TODO
func HostRelationWatchList(client *Client) (Interface, error) {
	w := newHostRelationWatcher(client)
	go w.sync()
	return w, nil
}

func (w *HostRelationWatcher) sync() {
	var cursor string
	for {
		result, err := resourceWatch(w.client, HostRelationResource, cursor, w.fields)
		if err != nil {
			w.emit(Event{
				Type:   Error,
				Object: fmt.Sprintf("HostRelationWatcher failed: %v", err),
			})
			// 出现异常，重置cursor
			cursor = ""
			continue
		}
		glog.Infof("HostRelationWatcher - Cursor: %s, RequestId: %s, EventCount: %d",
			cursor,
			result.RequestId,
			len(result.BKEvents))
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
			var relation HostBizModule
			if err := json.Unmarshal(item.BKDetail, &relation); err != nil {
				w.emit(Event{
					Type:   Error,
					Object: fmt.Sprintf("TypeErr host_relation: Detail: %v - Err: %s", string(item.BKDetail), err),
				})
				continue
			}
			w.emit(Event{
				Key:    strconv.Itoa(relation.BKHostId),
				Object: &relation,
				Type:   EventType(item.BKEventType),
				Cursor: item.BKCursor,
			})
		}
	}
}

// ResultChan TODO
// Return event chan
func (w *HostRelationWatcher) ResultChan() <-chan Event {
	return w.outgoing
}

// Stop watcher
func (w *HostRelationWatcher) Stop() {
	w.lock.Lock()
	defer w.lock.Unlock()
	// Prevent double channel closes.
	if !w.stopped {
		w.stopped = true
		close(w.outgoing)
	}
}
