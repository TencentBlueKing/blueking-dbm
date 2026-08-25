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

package mysql

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestTdbctlNodeReplInfoUnmarshalJSON(t *testing.T) {
	t.Run("legacy keys", func(t *testing.T) {
		data := `{"Master_Host":"192.168.1.1","Master_Port":3306,"Slave_IO_Running":"Yes",` +
			`"Slave_SQL_Running":"Yes","Relay_Master_Log_File":"mysql-bin.000003","Exec_Master_Log_Pos":"154"}`
		info := &TdbctlNodeReplInfo{}
		require.NoError(t, json.Unmarshal([]byte(data), info))

		assert.Equal(t, "192.168.1.1", info.MasterHost)
		assert.Equal(t, 3306, info.MasterPort)
		assert.Equal(t, "Yes", info.SlaveIORunning)
		assert.Equal(t, "Yes", info.SlaveSQLRunning)
		assert.Equal(t, "mysql-bin.000003", info.RelayMasterLogFile)
		assert.Equal(t, "154", info.ExecMasterLogPos)
	})

	t.Run("replica keys", func(t *testing.T) {
		data := `{"Source_Host":"192.168.1.1","Source_Port":3306,"Replica_IO_Running":"Yes",` +
			`"Replica_SQL_Running":"No","Relay_Source_Log_File":"mysql-bin.000004","Exec_Source_Log_Pos":"200"}`
		info := &TdbctlNodeReplInfo{}
		require.NoError(t, json.Unmarshal([]byte(data), info))

		assert.Equal(t, "192.168.1.1", info.MasterHost)
		assert.Equal(t, 3306, info.MasterPort)
		assert.Equal(t, "Yes", info.SlaveIORunning)
		assert.Equal(t, "No", info.SlaveSQLRunning)
		assert.Equal(t, "mysql-bin.000004", info.RelayMasterLogFile)
		assert.Equal(t, "200", info.ExecMasterLogPos)
	})

	t.Run("legacy keys win when mixed", func(t *testing.T) {
		data := `{"Master_Host":"192.168.1.1","Source_Host":"192.168.1.2","Master_Port":3306,` +
			`"Slave_SQL_Running":"Yes","Replica_SQL_Running":"No",` +
			`"Relay_Master_Log_File":"mysql-bin.000005","Exec_Master_Log_Pos":"300"}`
		info := &TdbctlNodeReplInfo{}
		require.NoError(t, json.Unmarshal([]byte(data), info))

		assert.Equal(t, "192.168.1.1", info.MasterHost)
		assert.Equal(t, 3306, info.MasterPort)
		assert.Equal(t, "Yes", info.SlaveSQLRunning)
		assert.Equal(t, "mysql-bin.000005", info.RelayMasterLogFile)
		assert.Equal(t, "300", info.ExecMasterLogPos)
	})
}
