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

const (
	// Define variables for all the field names of the database tables
	// to avoid hard-coding the field names in the business code.
	SkipDbInstanceFieldBkCloudID    = "bk_cloud_id"
	SkipDbInstanceFieldBkBizID      = "bk_biz_id"
	SkipDbInstanceFieldInstanceIP   = "instance_ip"
	SkipDbInstanceFieldInstancePort = "instance_port"
	SkipDbInstanceFieldCreatedAt    = "created_at"
	SkipDbInstanceFieldUpdatedAt    = "updated_at"
	SkipDbInstanceFieldDeletedAt    = "deleted_at"
)

type SkipDbInstance struct {
	BkCloudID    int       `gorm:"column:bk_cloud_id;primaryKey"`
	BkBizID      int       `gorm:"column:bk_biz_id;primaryKey"`
	InstanceIP   string    `gorm:"column:instance_ip;primaryKey"`
	InstancePort int       `gorm:"column:instance_port;premaryKey"`
	CreatedAt    time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt    time.Time `gorm:"column:updated_at;autoUpdateTime"`
	DeletedAt    time.Time `gorm:"column:deleted_at"`
}

func (t SkipDbInstance) TableName() string {
	return "t_skip_dbinstance"
}
