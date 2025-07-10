package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"time"

	reversecommonapi "dbm-services/common/reverseapi/apis/common"
	reversecommondef "dbm-services/common/reverseapi/define/common"
	"dbm-services/common/reverseapi/internal/core"
)

type demoEvent struct {
	bkBizId  int64
	Filename string `json:"filename"`
}

func (c *demoEvent) ClusterType() string {
	return "tendbsingle"
}

func (c *demoEvent) EventType() string {
	return "mysql-backup"
}

func (c *demoEvent) EventCreateTimeStamp() int64 {
	return time.Now().UnixMilli()
}

func (c *demoEvent) EventBkBizId() int64 {
	return c.bkBizId
}

// 不强求实现 String, 这里是给下面的错误处理写例子用的
func (c *demoEvent) String() string {
	b, _ := json.Marshal(c)
	return string(b)
}

func main() {
	flag.Parse()
	apiCore := core.NewDebugCore(0, flag.Arg(0), flag.Arg(1))

	event := &demoEvent{
		bkBizId:  21,
		Filename: "demo-file-0",
	}
	err := ReportEvent(apiCore, event)
	if err != nil {
		// 利用错误类型断言可以抽取出错的 event 和原因
		var serr reversecommondef.SyncReportError[*demoEvent] // 上报接口用到了 go 泛型
		if errors.As(err, &serr) {
			fmt.Printf("all error details: %s\n", serr.ErrDetail())

			for _, sd := range serr.ErrDetail() {
				fmt.Printf("event: %s, reason: %s\n", sd.Event, sd.Reason)
			}
			os.Exit(1)
		}
		panic(err)
	}
}

func ReportEvent(ac *core.Core, event *demoEvent) error {
	_, err := reversecommonapi.SyncReport(ac, event)
	if err != nil {
		//// 利用错误类型断言可以抽取出错的 event 和原因
		//var serr reversecommondef.SyncReportError[*demoEvent] // 上报接口用到了 go 泛型
		//if errors.As(err, &serr) {
		//	fmt.Printf("all error details: %s\n", serr.ErrDetail())
		//
		//	for _, sd := range serr.ErrDetail() {
		//		fmt.Printf("event: %s, reason: %s\n", sd.Event, sd.Reason)
		//	}
		//	os.Exit(1)
		//}
		return err
	}
	return nil
}
