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

// ModuleWatcher is a the ModuleWatcher server
type ModuleWatcher struct {
	client   *Client
	fields   []string
	lock     sync.Mutex
	stopped  bool
	outgoing chan Event
	emit     func(Event)
}

func newModuleWatcher(client *Client) *ModuleWatcher {
	w := &ModuleWatcher{
		client:   client,
		fields:   utils.GetStructTagName(reflect.TypeOf(&Module{})),
		outgoing: make(chan Event),
	}
	w.emit = func(e Event) { w.outgoing <- e }
	return w
}

// ModuleWatchList TODO
func ModuleWatchList(client *Client) (Interface, error) {
	w := newModuleWatcher(client)
	go w.sync()
	return w, nil
}

func (w *ModuleWatcher) sync() {
	var cursor string
	for {
		result, err := resourceWatch(w.client, ModuleResource, cursor, w.fields)
		if err != nil {
			w.emit(Event{
				Type:   Error,
				Object: fmt.Sprintf("ModuleWatcher failed: %v", err),
			})
			// 出现异常，重置cursor
			cursor = ""
			continue
		}
		glog.Infof("ModuleWatcher - Cursor: %s, RequestId: %s, EventCount: %d",
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
			var module Module
			if err := json.Unmarshal(item.BKDetail, &module); err != nil {
				w.emit(Event{
					Type:   Error,
					Object: fmt.Sprintf("TypeErr module: Detail: %v - Err: %s", string(item.BKDetail), err),
				})
				continue
			}
			w.emit(Event{
				Key:    strconv.Itoa(module.BKModuleId),
				Object: &module,
				Type:   EventType(item.BKEventType),
			})
		}
	}
}

// ResultChan TODO
// Return event chan
func (w *ModuleWatcher) ResultChan() <-chan Event {
	return w.outgoing
}

// Stop watcher
func (w *ModuleWatcher) Stop() {
	w.lock.Lock()
	defer w.lock.Unlock()
	// Prevent double channel closes.
	if !w.stopped {
		w.stopped = true
		close(w.outgoing)
	}
}
