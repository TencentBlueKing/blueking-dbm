/*
 * @Description: Mock test
 */
package mock

import "testing"

func TestMockDbbackupConfig(t *testing.T) {
	t.Log("start ...")
	d := MockMysqlDbBackupConfigs()
	t.Log(d)
	t.Log("end ...")
}

func TestMockRotateBinlogConfig(t *testing.T) {
	t.Log("start ...")
	MockMysqlRotateConfigs()
	// t.Log(d)
	t.Log("end ...")
}
