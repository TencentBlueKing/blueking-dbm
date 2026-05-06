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

package haprobe

// InnoDBStatus InnoDB engine status
type InnoDBStatus struct {
	InnodbBackgroundLogSync       uint64  `json:"innodb_background_log_sync,omitempty"`
	InnodbLogWriteRequests        uint64  `json:"innodb_log_write_requests,omitempty"`
	InnodbLogWrites               uint64  `json:"innodb_log_write_times,omitempty"`
	InnodbOsLogFsyncs             uint64  `json:"innodb_os_log_fsyncs,omitempty"`
	InnodbBufferPoolPagesDirty    uint64  `json:"innodb_buffer_pool_pages_dirty,omitempty"`
	InnodbBufferPoolPagesFlushed  uint64  `json:"innodb_buffer_pool_pages_flushed,omitempty"`
	InnodbBufferPoolPagesTotal    uint64  `json:"innodb_buffer_pool_pages_total,omitempty"`
	InnodbBufferPoolPagesFree     uint64  `json:"innodb_buffer_pool_pages_free,omitempty"`
	InnodbBufferPoolPagesData     uint64  `json:"innodb_buffer_pool_pages_pages_data,omitempty"`
	InnodbBufferPoolBytesData     uint64  `json:"innodb_buffer_pool_pages_bytes_data,omitempty"`
	InnodbBufferPoolWriteRequests uint64  `json:"innodb_buffer_pool_write_requests,omitempty"`
	InnodbBufferPoolReadRequests  uint64  `json:"innodb_buffer_pool_reads_requests,omitempty"`
	InnodbBufferPoolHitRate       float64 `json:"innodb_buffer_pool_hit_rate,omitempty"`
	InnodbRowsRead                uint64  `json:"innodb_row_reads,omitempty"`
	InnodbRowsInserted            uint64  `json:"innodb_row_inserted,omitempty"`
	InnodbRowsUpdated             uint64  `json:"innodb_row_updated,omitempty"`
	InnodbRowsDeleted             uint64  `json:"innodb_row_deleted,omitempty"`
	InnodbDataWrites              uint64  `json:"innodb_data_written,omitempty"`
	InnodbDblwrPagesWritten       uint64  `json:"innodb_dblwr_pages_written,omitempty"`
	InnodbRowLockWaitsTime        uint64  `json:"innodb_row_lock_waits_time,omitempty"`
	InnodbTableLockWaitsNum       uint64  `json:"innodb_table_lock_waits_num,omitempty"`
	InnodbRowLockWaitsNum         uint64  `json:"innodb_row_lock_waits_num,omitempty"`
}
