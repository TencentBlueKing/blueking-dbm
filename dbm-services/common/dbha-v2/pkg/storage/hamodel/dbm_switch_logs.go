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

package hamodel

import "time"

// HASwitchLogs TODO
type HASwitchLogs struct {
	UID      int64      `gorm:"column:uid;type:bigint;primaryKey;autoIncrement" json:"uid,omitempty"`
	SwitchID int64      `gorm:"column:sw_id;type:bigint;index:idx_sw_id"        json:"sw_id,omitempty"`
	App      string     `gorm:"column:app;type:varchar(32);NOT NULL"            json:"app,omitempty"`
	IP       string     `gorm:"column:ip;type:varchar(32);index:idx_ip_port"    json:"ip,omitempty"`
	Port     int        `gorm:"column:port;type:int(11);index:idx_ip_port"      json:"port,omitempty"`
	Result   string     `gorm:"column:result;type:tinyblob"                     json:"result,omitempty"`
	Datetime *time.Time `gorm:"column:datetime;type:datetime;index:idx_date"    json:"datetime,omitempty"`
	Comment  string     `gorm:"column:comment;type:blob"                        json:"comment,omitempty"`
}

// TableName TODO
func (s *HASwitchLogs) TableName() string {
	return "ha_switch_logs"
}
