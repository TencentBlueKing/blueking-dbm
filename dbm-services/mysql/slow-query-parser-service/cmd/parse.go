/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmd

import (
	"fmt"
	"os"
	"time"

	"github.com/percona/go-mysql/event"
	"github.com/percona/go-mysql/log"
	"github.com/percona/go-mysql/log/slow"

	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"
)

type ClassExt struct {
	class     *event.Class
	firstSeen time.Time
	lastSean  time.Time
	countStar int64
	//SchemaName string
	//TableName  string
	Tables []string
}

func (c *ClassExt) String() string {
	return fmt.Sprintf("%s | %d %d | %v |'%s','%s' | %s",
		c.class.Id, c.class.TotalQueries, c.countStar, c.Tables,
		c.firstSeen, c.lastSean,
		c.class.Fingerprint)
}

// Execute 测试定期扫描 slow
func Execute() {
	slowLogFile := "./slow-query.log"
	f, err := os.OpenFile(slowLogFile, os.O_RDONLY, 0644)
	if err != nil {
		panic(err)
	}
	sp := slow.NewSlowLogParser(f, log.Options{})
	go func() {
		sp.Start()
	}()

	// 异步打印
	allClass := map[string]*ClassExt{}
	go func() {
		for {
			fmt.Println()
			fmt.Println("=====================================")

			time.Sleep(1 * time.Second)
			for _, class := range allClass {
				//class.class.Finalize(0)
				if class.class.Id == "eb7ff14619afa214" {
					fmt.Println("--------------------------")
					fmt.Println(class)
				}
			}
		}
	}()
	for {
		select {
		case ev := <-sp.EventChan():
			//fmt.Println(ev.Db, ev.User, ev.Host, " | ", ev.Query)
			if resp, err := mysql.AnalyzeSql(ev.Db, ev.Query); err == nil {
				time.Sleep(20 * time.Millisecond)
				// class 就是一个 finerprint
				cl := event.NewClass(resp.QueryDigestMd5, ev.User, ev.Host, ev.Db, "", resp.QueryDigestText, false)
				if _, ok := allClass[resp.QueryDigestMd5]; !ok {
					allClass[resp.QueryDigestMd5] = &ClassExt{
						class:     cl,
						firstSeen: ev.Ts,
						lastSean:  ev.Ts,
						countStar: 1,
					}
					for _, dbtb := range resp.TableReferences {
						allClass[resp.QueryDigestMd5].Tables = append(allClass[resp.QueryDigestMd5].Tables, dbtb.String())
					}
				} else {
					allClass[resp.QueryDigestMd5].class.AddEvent(ev, false)
					allClass[resp.QueryDigestMd5].lastSean = ev.Ts
					allClass[resp.QueryDigestMd5].countStar++
				}
				cl.AddEvent(ev, false)
			}
		case <-time.After(100 * time.Millisecond):
			fmt.Println("sleep 100ms")
			time.Sleep(100 * time.Millisecond)
		}
	}
}
