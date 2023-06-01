package native_test

import (
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// BenchmarkDbConn TODO
func BenchmarkDbConn(b *testing.B) {
	d, err := native.NewDbWorker(native.DsnBySocket("/data/mysql/3306/mysql.sock", "root", ""))
	if err != nil {
		b.Fatalf("connect failed %s", err.Error())
		return
	}
	for n := 0; n < b.N; n++ {
		d.SelectLongRunningProcesslist(0)
	}
}
