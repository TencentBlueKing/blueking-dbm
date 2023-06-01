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

// SetWatcher is a the SetWatcher server
type SetWatcher struct {
	client   *Client
	fields   []string
	lock     sync.Mutex
	stopped  bool
	outgoing chan Event
	emit     func(Event)
}

func newSetWatcher(client *Client) *SetWatcher {
	w := &SetWatcher{
		client:   client,
		fields:   utils.GetStructTagName(reflect.TypeOf(&Set{})),
		outgoing: make(chan Event),
	}
	w.emit = func(e Event) { w.outgoing <- e }
	return w
}

// SetWatchList TODO
func SetWatchList(client *Client) (Interface, error) {
	w := newSetWatcher(client)
	go w.sync()
	return w, nil
}

func (w *SetWatcher) sync() {
	var cursor string
	for {
		result, err := resourceWatch(w.client, SetResource, cursor, w.fields)
		if err != nil {
			w.emit(Event{
				Type:   Error,
				Object: fmt.Sprintf("SetWatcher failed: %v", err),
			})
			// 出现异常，重置cursor
			cursor = ""
			continue
		}
		glog.Infof("SetWatcher - Cursor: %s, RequestId: %s, EventCount: %d", cursor, result.RequestId, len(result.BKEvents))
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
			var set Set
			if err := json.Unmarshal(item.BKDetail, &set); err != nil {
				w.emit(Event{
					Type:   Error,
					Object: fmt.Sprintf("TypeErr set: Err: %v - Detail: %s", err, string(item.BKDetail)),
				})
				continue
			}
			w.emit(Event{
				Key:    strconv.Itoa(set.BKSetId),
				Object: &set,
				Type:   EventType(item.BKEventType),
			})
		}
	}
}

// ResultChan TODO
// Return event chan
func (w *SetWatcher) ResultChan() <-chan Event {
	return w.outgoing
}

// Stop watcher
func (w *SetWatcher) Stop() {
	w.lock.Lock()
	defer w.lock.Unlock()
	// Prevent double channel closes.
	if !w.stopped {
		w.stopped = true
		close(w.outgoing)
	}
}
