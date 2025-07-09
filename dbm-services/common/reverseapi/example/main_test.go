package main

import (
	"dbm-services/common/reverseapi/apis/common"
	"dbm-services/common/reverseapi/internal/core"
	"fmt"
	"testing"
)

func benchmarkReport(b *testing.B, buckSize int) {
	//flag.Parse()
	//apiCore := core.NewDebugCore(0, flag.Arg(0), flag.Arg(1))
	apiCore := core.NewCore(0, "1.1.1.1:80")
	var events []*demoEvent
	for i := 0; i < buckSize; i++ {
		events = append(events, &demoEvent{
			bkBizId:  21,
			Filename: fmt.Sprintf("filename-%d-%d", buckSize, i),
		})
	}
	b.SetParallelism(4)
	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {

		for pb.Next() {
			_, err := common.SyncReport(apiCore, events...)
			if err != nil {
				b.Error(err)
			}
		}
	})

	//}
}

func BenchmarkReportEvent1(b *testing.B) {
	benchmarkReport(b, 1)
}

func BenchmarkReportEvent2(b *testing.B) {
	benchmarkReport(b, 2)
}

func BenchmarkReportEvent4(b *testing.B) {
	benchmarkReport(b, 4)
}

func BenchmarkReportEvent8(b *testing.B) {
	benchmarkReport(b, 8)
}

func BenchmarkReportEvent16(b *testing.B) {
	benchmarkReport(b, 16)
}

func BenchmarkReportEvent32(b *testing.B) {
	benchmarkReport(b, 32)
}

func BenchmarkReportEvent64(b *testing.B) {
	benchmarkReport(b, 64)
}

func BenchmarkReportEvent128(b *testing.B) {
	benchmarkReport(b, 128)
}

func BenchmarkReportEvent256(b *testing.B) {
	benchmarkReport(b, 256)
}

func BenchmarkReportEvent512(b *testing.B) {
	benchmarkReport(b, 512)
}
