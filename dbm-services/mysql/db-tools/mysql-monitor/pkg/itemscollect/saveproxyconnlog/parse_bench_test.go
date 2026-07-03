package saveproxyconnlog

import "testing"

// 测试用例：匹配的 conn_log 行
var benchLines = []string{
	"2026-06-29 23:55:07: (critical) conn_log, current user is 'user1'@'1.2.3.4' 147550633",
	"2026-06-29 23:55:07: (critical) conn_log, current user is 'user2'@'1.2.3.4' 147550640",
	"2026-06-29 23:55:07: (critical) conn_log, current user is 'user3'@'1.2.3.4' 147550643",
	"2026-06-30 10:22:15: (critical) conn_log, current user is 'user4'@'1.2.3.4' 999999999",
}

// 测试用例：不匹配的行（大部分日志行都是这种）
var benchNonMatchLines = []string{
	"2026-06-29 23:55:07: (message) proxy connected",
	"2026-06-29 23:55:07: (critical) some other critical message here",
	"2026-06-29 23:55:08: (warning) connection pool exhausted",
	"",
	"random garbage line without any structure",
}

// BenchmarkParseConnLogLine 正则版本 - 匹配行
func BenchmarkParseConnLogLine(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		for _, line := range benchLines {
			parseConnLogLine(line)
		}
	}
}

// BenchmarkParseConnLogLineV2 字符串切片版本 - 匹配行
func BenchmarkParseConnLogLineV2(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		for _, line := range benchLines {
			parseConnLogLineV2(line)
		}
	}
}

// BenchmarkParseConnLogLine_NonMatch 正则版本 - 不匹配行
func BenchmarkParseConnLogLine_NonMatch(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		for _, line := range benchNonMatchLines {
			parseConnLogLine(line)
		}
	}
}

// BenchmarkParseConnLogLineV2_NonMatch 字符串切片版本 - 不匹配行
func BenchmarkParseConnLogLineV2_NonMatch(b *testing.B) {
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		for _, line := range benchNonMatchLines {
			parseConnLogLineV2(line)
		}
	}
}

// BenchmarkParseConnLogLine_Mixed 正则版本 - 混合场景（模拟真实比例：80%不匹配 + 20%匹配）
func BenchmarkParseConnLogLine_Mixed(b *testing.B) {
	mixed := make([]string, 0, 20)
	// 16 行不匹配
	for i := 0; i < 4; i++ {
		mixed = append(mixed, benchNonMatchLines...)
	}
	// 4 行匹配
	mixed = append(mixed, benchLines...)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		for _, line := range mixed {
			parseConnLogLine(line)
		}
	}
}

// BenchmarkParseConnLogLineV2_Mixed 字符串切片版本 - 混合场景
func BenchmarkParseConnLogLineV2_Mixed(b *testing.B) {
	mixed := make([]string, 0, 20)
	// 16 行不匹配
	for i := 0; i < 4; i++ {
		mixed = append(mixed, benchNonMatchLines...)
	}
	// 4 行匹配
	mixed = append(mixed, benchLines...)

	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		for _, line := range mixed {
			parseConnLogLineV2(line)
		}
	}
}
