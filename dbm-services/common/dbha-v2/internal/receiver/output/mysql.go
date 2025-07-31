/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package output

import (
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"encoding/json"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const mySQLName = "MySQL"

// Message Data message reported by probe.
type Message struct {
	Topic string
	Data  []byte
}

type mySQL struct {
	dbs []*hamysql.DB
}

func newMySQL(endpoints, user, password string) (*mySQL, error) {
	epoints, err := hanet.NewEndpoints(endpoints)
	if err != nil {
		return nil, err
	}

	msql := &mySQL{}

	for _, epoint := range epoints {

		db, err := hamysql.New(
			hamysql.OptionIP(epoint.Host),
			hamysql.OptionPort(epoint.Port),
			hamysql.OptionProto(epoint.Proto),
			hamysql.OptionDBName(hamodel.DatabaseName),
			hamysql.OptionUser(user),
			hamysql.OptionPassword(password))

		if err != nil {
			return nil, err
		}

		msql.dbs = append(msql.dbs, db)
	}

	return msql, nil
}

func (s *mySQL) Save(msg *Message) error {
	mysqlMetric := &haprobe.MySQLMetric{}
	if err := json.Unmarshal([]byte(msg.Data), mysqlMetric); err != nil {
		return gerrors.Newf(gerrors.InvalidJSOIN, "unmarshal a mysql metric message failed, topic(%s), %v", msg.Topic, err)
	}

	logger.Debug("outputter(mysql) save msg(%v)", string(msg.Data))

	if len(mysqlMetric.Databases) == 0 {
		return gerrors.Newf(gerrors.InvalidJSOIN, "unmarshal a mysql metric message failed, topic(%s), data(%v)",
			msg.Topic, *mysqlMetric)
	}

	data := hamodel.NewDBHAMySQL(mysqlMetric)

	for _, db := range s.dbs {
		err := db.DB().Session(&gorm.Session{FullSaveAssociations: true}).
			Clauses(clause.OnConflict{UpdateAll: true}).
			Create(data).Error

		if err != nil {
			logger.Warn("save the mysql metric failed, %v", err)
		}
	}

	return nil
}

func (s *mySQL) Close() {
}
